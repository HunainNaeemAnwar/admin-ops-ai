import json
from datetime import date
from typing import Optional

import agent_system.provider

from openai import RateLimitError, APIStatusError
from agents import Agent, Runner, function_tool, ModelSettings
from config import GEMINI_MODEL, FALLBACK_MODELS, FIXED_WORKERS, PDF_DIR, EXCEL_SLIPS_DIR
from tools.production_tools import (
    log_production_json,
    mark_absent as prod_mark_absent,
    mark_all_absent,
    update_entry as prod_update_entry,
)
from tools.rejection_tools import log_rejection as rej_log
from tools.advance_tools import record_advance as adv_record
from tools.report_tools import get_daily_status as status_get, get_summary as summary_get
from tools.export_tools import generate_excel_report
from tools.payslip_tools import generate_pdf_payslip, generate_excel_payslip
from tools.database import (
    get_active_workers, get_all_products, get_worker_id,
    get_total_advances_for_worker_month,
    get_worker_month_production,
    save_payslip,
)
from agent_system.memory_manager import ConversationMemory


_memories: dict[str, ConversationMemory] = {}


def _get_memory(session_id: str = "default") -> ConversationMemory:
    if session_id not in _memories:
        _memories[session_id] = ConversationMemory(session_id)
    return _memories[session_id]


def _dynamic_instructions(ctx, agent) -> str:
    today = date.today()
    today_str = today.isoformat()
    workers_str = ", ".join(FIXED_WORKERS)
    return f"""# Purpose

You are a factory production accounting system. You record daily production, track rejections and advances, generate payslips, and email reports. You are NOT a chatbot. You are a tool execution engine.

# Fixed Data

- Workers: {workers_str}
- Today: {today_str}
- Products (EXACT codes only, no aliases): NUT, 10*20, 6*25, 6*30, 10*25

# Core Behavior Rules

- A single user message may contain MULTIPLE instructions (e.g. "record production for Kaleem, then mark Naeem absent, then show daily status"). Execute ALL of them in one response. Do NOT ask "should I continue?" between steps.
- Output ONLY the result of each tool call. No greetings, no "Main kar raha hoon", no "yeh lo result", no suggestions, no chit-chat.
- If a tool call FAILS (e.g. duplicate entry, unknown product), state the error concisely and move to the next instruction. Do NOT stop the entire sequence.
- Never auto-execute anything. Father must explicitly request every action.

# Tool Execution Rules

1. log_production_tool — EXTRACT data from user text YOURSELF and format as JSON. Call with entries_json parameter. Do NOT ask user to format data. Do NOT call any other tool for extraction.
2. log_rejection_tool — Parameters: year, month, product_code, total_qty, excluded_workers (optional JSON array or null).
3. record_advance_tool — Parameters: worker, amount, year, month, description (optional).
4. mark_absent_tool — Parameters: worker name or "all", date_str (default today). If worker already has production entries, report "Cannot mark absent — entries exist for this date".
5. get_daily_status_tool — Returns DATA_FOUND or NO_DATA. Show the raw output without rephrasing.
6. get_summary_tool — Call with period="daily"|"weekly"|"monthly". Show raw output.
7. generate_payslip_tool — Parameters: year, month, worker (or null/empty for ALL workers). Show raw confirmation.
8. send_report_tool — Quantities ONLY. Never include worker names, financial data, or individual pay. Parameter: period, year, month, day.
9. update_entry_tool — Parameters: entry_id, new_quantity, reason (optional). Show old vs new.
10. list_catalog_tool — Call at conversation start. No parameters.

# Output Format

- Each tool call result is returned directly. Never rephrase or add explanations.
- For multi-instruction messages, generate multiple tool calls in one turn.
- Do NOT generate text — only tool calls.

# Examples

## Example 1: Single production entry
User: Kaleem ne 300 nut kiye
Agent: log_production_tool(entries_json='[{"worker":"Kaleem","product_code":"NUT","quantity":300}]')

## Example 2: Multiple instructions in one message
User: Kaleem ne 300 nut aur 150 10*20 kiye. Naeem ko absent mark karo. Aaj ka status do.
Agent: log_production_tool(entries_json='[{"worker":"Kaleem","product_code":"NUT","quantity":300},{"worker":"Kaleem","product_code":"10*20","quantity":150}]')
Agent: mark_absent_tool(workers="Naeem")
Agent: get_daily_status_tool()

## Example 3: Error in sequence
User: Kaleem ko 2000 advance do June 2026. Unknown worker ko 500 advance do.
Agent: record_advance_tool(worker="Kaleem", amount=2000, year=2026, month=6)
Agent: record_advance_tool(worker="Unknown", amount=500, year=2026, month=6)

## Example 4: Rejection with distribution
User: June 2026 mein 500 nut reject
You: Rejection recorded (id=1): 500xNUT for 2026-06
Eligible (8): 62 each, extra: Naeem, Kaleem, Akbar, Suny"""


@function_tool
def log_production_tool(entries_json: str) -> str:
    """Record daily production. Extract worker, product_code, quantity from user text yourself and format as JSON.

    Args:
        entries_json: JSON array string. Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]

    Returns:
        Confirmation per entry
    """
    return log_production_json(entries_json)


@function_tool
def log_rejection_tool(year: int, month: int, product_code: str, total_qty: int, excluded_workers: Optional[str] = None) -> str:
    """Record department-level rejection for a month. Rejection is equally distributed among eligible workers.

    Args:
        year: Year (e.g. 2026)
        month: Month number 1-12
        product_code: Product code (NUT, 10*20, 6*25, 6*30, 10*25)
        total_qty: Total rejected pieces at department level
        excluded_workers: JSON array of worker names to exclude from distribution, or null

    Returns:
        Confirmation with distribution breakdown showing each worker's share
    """
    excluded = []
    if excluded_workers:
        try:
            excluded = json.loads(excluded_workers)
        except (json.JSONDecodeError, TypeError):
            excluded = [excluded_workers]
    return rej_log(year, month, product_code, total_qty, excluded)


@function_tool
def record_advance_tool(worker: str, amount: float, year: int, month: int, description: Optional[str] = None) -> str:
    """Record an advance payment given to a worker.

    Args:
        worker: Worker name (e.g. 'Kaleem')
        amount: Advance amount in rupees
        year: Year (e.g. 2026)
        month: Month number 1-12
        description: Optional reason for the advance

    Returns:
        Confirmation with total advances for this worker this month
    """
    desc = description or ""
    return adv_record(worker, amount, year, month, desc)


@function_tool
def mark_absent_tool(workers: str, date_str: Optional[str] = None) -> str:
    """Mark workers as absent for a given date. Affects daily status checks.

    Args:
        workers: Worker name (e.g. 'Kaleem') or 'all' to mark all workers absent
        date_str: Date in YYYY-MM-DD format (default: today)

    Returns:
        Confirmation of which workers were marked absent
    """
    if date_str is None:
        date_str = date.today().isoformat()
    if workers.lower() == "all":
        return mark_all_absent(date_str)
    return prod_mark_absent(workers, date_str)


@function_tool
def get_daily_status_tool(date_str: Optional[str] = None) -> str:
    """Check if production data exists for a date. Returns DATA_FOUND or NO_DATA with details.

    Args:
        date_str: Date in YYYY-MM-DD format (default: today)

    Returns:
        Status message with present/absent workers and product totals
    """
    return status_get(date_str)


@function_tool
def get_summary_tool(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Get production summary for a period. Quantities only - no financial data.

    Args:
        period: 'daily', 'weekly', or 'monthly' (default: 'daily')
        year: Year (default: current)
        month: Month 1-12 (default: current)
        day: Day 1-31 (default: today)

    Returns:
        Formatted summary with product totals per worker per day
    """
    return summary_get(period, year, month, day)


@function_tool
def generate_payslip_tool(year: int, month: int, worker: Optional[str] = None) -> str:
    """Generate PDF + Excel payslip for one worker or all workers for a given month.
    Calculates gross, rejection deduction, advance deduction, tax, and net payable.

    Args:
        year: Year (e.g. 2026)
        month: Month number 1-12
        worker: Worker name for single payslip, or null/empty for ALL workers

    Returns:
        File paths for generated payslips with breakdown summary
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    from config import TAX_PERCENTAGE
    from tools.rejection_tools import get_distribution_for_month

    distribution = get_distribution_for_month(y, m)

    if worker:
        workers_list = [worker]
    else:
        workers_list = [w["name"] for w in get_active_workers()]

    results = []
    for w in workers_list:
        wid = get_worker_id(w)
        if not wid:
            results.append(f"  {w}: Unknown worker")
            continue

        production = get_worker_month_production(wid, y, m)
        if not production:
            results.append(f"  {w}: No production data for {y}-{m:02d}")
            continue

        product_totals = {}
        for p in production:
            code = p["product_code"]
            product_totals[code] = product_totals.get(code, 0) + p["quantity"]

        gross_total = 0.0
        from tools.production_tools import get_product_info
        for code, qty in product_totals.items():
            product = get_product_info(code)
            if product:
                gross_total += qty * product["rate"]

        rejection_qty = 0
        for dist in distribution:
            w_share = dist["distribution"].get(w, 0)
            product = get_product_info(dist["product_code"])
            if product:
                rejection_qty += w_share * product["rate"]

        advance_total = get_total_advances_for_worker_month(wid, y, m)

        tax_amount = round(gross_total * TAX_PERCENTAGE / 100, 2)
        net_payable = round(gross_total - rejection_qty - advance_total - tax_amount, 2)

        save_payslip(wid, y, m, gross_total, tax_amount, rejection_qty, advance_total, net_payable)
        pdf_path = generate_pdf_payslip(w, y, m)
        xls_path = generate_excel_payslip(w, y, m)

        results.append(
            f"  {w}: Gross Rs {gross_total:,.2f}, "
            f"Reject Rs {rejection_qty:,.2f}, "
            f"Advance Rs {advance_total:,.2f}, "
            f"Tax Rs {tax_amount:,.2f}, "
            f"Net Rs {net_payable:,.2f}\n"
            f"    PDF: {pdf_path}\n    Excel: {xls_path}"
        )

    if not results:
        return "No payslips generated."
    return f"Payslips for {y}-{m:02d}:\n" + "\n".join(results)


@function_tool
def send_report_tool(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Send production summary email to the manager. Quantities only - no financials, no individual data.

    Args:
        period: 'daily', 'weekly', or 'monthly' (default: 'daily')
        year: Year (default: current)
        month: Month 1-12 (default: current)
        day: Day 1-31 (default: today)

    Returns:
        Email delivery status
    """
    from tools.email_tools import send_summary
    today = date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day
    return send_summary(period, y, m, d)


@function_tool
def update_entry_tool(entry_id: int, new_quantity: int, reason: Optional[str] = None) -> str:
    """Update the quantity of an existing production entry.

    Args:
        entry_id: Entry ID from daily_log (shown in status/summary outputs)
        new_quantity: New quantity value (must be positive)
        reason: Optional reason for the change

    Returns:
        Old vs new values confirmation
    """
    rsn = reason or ""
    return prod_update_entry(entry_id, new_quantity, rsn)


@function_tool
def list_catalog_tool() -> str:
    """List all workers, products with rates, and today's production status.

    Returns:
        Catalog info including worker list, product rates, and current date
    """
    today = date.today()
    workers = get_active_workers()
    products = get_all_products()

    lines = [
        f"Today: {today.isoformat()}",
        f"",
        f"Workers ({len(workers)}):",
    ]
    for w in workers:
        lines.append(f"  {w['name']}")

    lines.append(f"\nProducts:")
    for p in products:
        lines.append(f"  {p['code']}: Rs {p['rate']:,.2f}/pc ({p['description']})")

    status = status_get()
    lines.append(f"\nToday's Status:")
    lines.append(f"  {status}")

    return "\n".join(lines)


def _create_agent(model: str | None = None) -> Agent:
    return Agent(
        name="AccountantOrchestrator",
        instructions=_dynamic_instructions,
        model=model or GEMINI_MODEL,
        model_settings=ModelSettings(
            temperature=0.1,
            top_p=0.9,
        ),
        tool_use_behavior="stop_on_first_tool",
        tools=[
            log_production_tool,
            log_rejection_tool,
            record_advance_tool,
            mark_absent_tool,
            get_daily_status_tool,
            get_summary_tool,
            generate_payslip_tool,
            send_report_tool,
            update_entry_tool,
            list_catalog_tool,
        ],
    )


async def chat(user_input: str, session_id: str = "default") -> str:
    memory = _get_memory(session_id)
    models = FALLBACK_MODELS

    for model in models:
        try:
            agent = _create_agent(model)
            result = await Runner.run(
                agent,
                input=user_input,
                session=memory.session,
            )
            return result.final_output
        except (RateLimitError, APIStatusError) as e:
            if len(models) == 1:
                return f"⚠️ Model {model} rate limited. No fallback models configured."
            continue

    return (
        f"⚠️ All AI models are currently rate-limited. "
        f"Tried: {', '.join(models)}. "
        f"Please try again in a few minutes."
    )
