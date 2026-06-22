import asyncio
import json
from datetime import date
from typing import Optional

import agent_system.provider

from openai import RateLimitError, APIStatusError
from agents import Agent, Runner, function_tool, ModelSettings
from agents.run_config import RunConfig
from agents.run_error_handlers import RunErrorHandlerResult, RunErrorHandlerInput
from config import FIXED_WORKERS, PDF_DIR, EXCEL_SLIPS_DIR
from agent_system.provider import ACTIVE_MODEL, get_model_by_name
from tools.production_tools import (
    log_production_json,
    mark_absent as prod_mark_absent,
    mark_all_absent,
    update_entry as prod_update_entry,
    parse_table_to_production,
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


# ── Instructions per specialist ───────────────────────

def _production_instructions(ctx, agent) -> str:
    return f"""<role>Factory production data entry assistant.</role>

<context>Workers: {', '.join(FIXED_WORKERS)}
Products: NUT, 10*20, 6*25, 6*30, 10*25 (convert ×/x → *)
Today: {date.today()}</context>

<rules>
- Single/few entries → log_production_tool with extracted JSON
- Multi-row tables (pasted with dates + product columns) → parse_table_tool
- Worker absent → mark_absent_tool
- Edit entry → update_entry_tool
- Combined production + absent → batch_daily_update_tool
- Return tool output directly
</rules>"""


def _reporting_instructions(ctx, agent) -> str:
    return f"""<role>Factory production reporting assistant. Quantities only — no individual or financial data.</role>

<context>Workers: {', '.join(FIXED_WORKERS)}
Products: NUT, 10*20, 6*25, 6*30, 10*25
Today: {date.today()}</context>

<rules>
- Status check → get_daily_status_tool
- Summary (daily/weekly/monthly) → get_summary_tool
- Show catalog/workers/products/list → list_catalog_tool
- Email to manager (quantities only) → send_report_tool
- Return tool output directly
</rules>"""


def _finance_instructions(ctx, agent) -> str:
    return f"""<role>Factory finance assistant handling rejections, advances, and payslips.</role>

<context>Workers: {', '.join(FIXED_WORKERS)}
Products: NUT, 10*20, 6*25, 6*30, 10*25
Today: {date.today()}</context>

<rules>
- Department rejection → log_rejection_tool (equally distributes among eligible workers)
- Worker advance payment → record_advance_tool
- Generate payslip PDF+Excel → generate_payslip_tool
- Return tool output directly
</rules>"""


def _router_instructions(ctx, agent) -> str:
    return f"""<role>Route user requests to the right specialist agent. Call ONE specialist per message.</role>

<context>Workers: {', '.join(FIXED_WORKERS)}
Products: NUT, 10*20, 6*25, 6*30, 10*25
Today: {date.today()}</context>

<rules>
1. Identify intent from user message
2. Route to the correct specialist
3. Return the specialist's output as-is

Routing:
- Production data entry, tables, absences, edits → delegate_production
- Summary, status, catalog, email reports → delegate_reporting
- Rejections, advances, payslips → delegate_finance
- Greeting, empty message, or uncertain → delegate_reporting (shows catalog by default)
</rules>"""


# ── Production Tools ──────────────────────────────────

@function_tool
def log_production_tool(entries_json: str) -> str:
    """Record single or multiple production entries using extracted JSON.

    Use for 1-5 entries where you can identify worker name, product code, and quantity from natural language.
    Example input: "Naeem made 300 NUT and 150 10*20"
    Example JSON: [{"worker":"Naeem","product_code":"NUT","quantity":300},{"worker":"Naeem","product_code":"10*20","quantity":150}]

    Do NOT use for pasted tables — use parse_table_tool instead.

    Args:
        entries_json: JSON array string. Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]

    Returns:
        Confirmation per entry
    """
    return log_production_json(entries_json)


@function_tool
def parse_table_tool(worker: str, table_text: str) -> str:
    """Parse a multi-row ASCII production table pasted by the user and record all entries.

    The table must have a DATE column and product columns (NUT, 6*30, 6*25, 10*20, 10*25).
    Handles box-drawing characters (┌─┐└┘├┤│) and plain pipe tables.
    Product codes can appear as 6×30, 6x30, 6*30 etc. — all auto-converted.
    When dates are in DD-MMM format (e.g. 1-Jun, 15-May), auto-fills the current year.

    Only call this when user pastes a multi-row table. NOT for single-line messages.

    Args:
        worker: Worker name (e.g. 'Naeem')
        table_text: Raw table text as pasted by user, including pipe/border characters

    Returns:
        Per-date results showing what was recorded
    """
    return parse_table_to_production(worker, table_text)


@function_tool
def mark_absent_tool(workers: str, date_str: Optional[str] = None) -> str:
    """Mark one or all workers as absent for a given date.

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
def update_entry_tool(entry_id: int, new_quantity: int, reason: Optional[str] = None) -> str:
    """Update the quantity of an existing production entry. Use when worker corrects a previous entry.

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
def batch_daily_update_tool(entries_json: str, absent_workers: Optional[str] = None) -> str:
    """Record production entries AND mark workers absent in a single call.

    Use when user provides both production data and absent workers together.
    For production-only or absent-only, use the individual tools instead.

    Args:
        entries_json: JSON array of production entries.
            Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]
        absent_workers: Optional JSON array of worker names to mark absent.
            Format: '["Naeem","Sajjad"]' or null

    Returns:
        Combined results of all operations
    """
    results = []
    try:
        parsed = json.loads(entries_json) if isinstance(entries_json, str) else entries_json
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            results.append("[Production] Invalid: must be an array")
        else:
            prod_result = log_production_json(json.dumps(parsed))
            results.append(f"[Production]\n{prod_result}")
    except (json.JSONDecodeError, TypeError) as e:
        results.append(f"[Production] Invalid JSON: {e}")

    if absent_workers:
        try:
            absent_list = json.loads(absent_workers) if isinstance(absent_workers, str) else absent_workers
            if isinstance(absent_list, str):
                absent_list = [absent_list]
            for w in absent_list:
                if isinstance(w, str) and w.strip():
                    results.append(prod_mark_absent(w.strip()))
        except (json.JSONDecodeError, TypeError) as e:
            results.append(f"[Absent] Invalid input: {e}")

    return "\n\n".join(results) if results else "No operations performed."


# ── Reporting Tools ───────────────────────────────────

@function_tool
def get_daily_status_tool(date_str: Optional[str] = None) -> str:
    """Check production data for a date — which workers have data, which are absent, and product totals.

    Args:
        date_str: Date in YYYY-MM-DD format (default: today)

    Returns:
        Status message with present/absent workers and product totals
    """
    return status_get(date_str)


@function_tool
def get_summary_tool(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Production summary for daily, weekly, or monthly period. Quantities only — no financial data.

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
def send_report_tool(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Email production summary to the manager. Quantities only — no financials, no individual worker data.

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
def list_catalog_tool() -> str:
    """List all workers, products with rates, and today's production status. Default response for greetings or empty messages.

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


# ── Finance Tools ─────────────────────────────────────

@function_tool
def log_rejection_tool(year: int, month: int, product_code: str, total_qty: int, excluded_workers: Optional[str] = None) -> str:
    """Record department-level rejection quantity for a month. Rejection value is equally distributed among eligible workers.

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
    """Record an advance payment given to a worker. Deducted automatically from their monthly payslip.

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
def generate_payslip_tool(year: int, month: int, worker: Optional[str] = None) -> str:
    """Generate PDF + Excel payslip for one worker or all workers for a given month.
    Calculates gross (quantity × rate), rejection deduction, advance deduction, tax percentage, and net payable.

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


# ── Agent factory ─────────────────────────────────────

def _create_agents(model_override=None):
    model = model_override or ACTIVE_MODEL
    base_settings = ModelSettings(
        temperature=0.1,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=True,
        tool_choice="required",
    )

    production_agent = Agent(
        name="ProductionAgent",
        instructions=_production_instructions,
        model=model,
        model_settings=base_settings,
        tools=[
            log_production_tool,
            parse_table_tool,
            mark_absent_tool,
            update_entry_tool,
            batch_daily_update_tool,
        ],
    )

    reporting_agent = Agent(
        name="ReportingAgent",
        instructions=_reporting_instructions,
        model=model,
        model_settings=base_settings,
        tools=[
            get_daily_status_tool,
            get_summary_tool,
            send_report_tool,
            list_catalog_tool,
        ],
    )

    finance_agent = Agent(
        name="FinanceAgent",
        instructions=_finance_instructions,
        model=model,
        model_settings=base_settings,
        tools=[
            log_rejection_tool,
            record_advance_tool,
            generate_payslip_tool,
        ],
    )

    router = Agent(
        name="Router",
        instructions=_router_instructions,
        model=model,
        model_settings=ModelSettings(
            temperature=0.1,
            top_p=0.9,
            max_tokens=2000,
            parallel_tool_calls=True,
            tool_choice="required",
        ),
        tools=[
            production_agent.as_tool(
                tool_name="delegate_production",
                tool_description="Route to production specialist for data entry, table parsing, absences, and entry edits.",
            ),
            reporting_agent.as_tool(
                tool_name="delegate_reporting",
                tool_description="Route to reporting specialist for summaries, status checks, catalog listing, and email reports. Use for greetings or unclear requests.",
            ),
            finance_agent.as_tool(
                tool_name="delegate_finance",
                tool_description="Route to finance specialist for rejection recording, advance payments, and payslip generation.",
            ),
        ],
    )
    return router


# ── Chat ──────────────────────────────────────────────

async def chat(user_input: str, session_id: str = "default") -> str:
    memory = _get_memory(session_id)
    await memory.cleanup()
    run_config = RunConfig(
        tool_not_found_behavior="return_error_to_model",
    )

    from config import LLM_PROVIDER, MISTRAL_API_KEY, GEMINI_API_KEY, CEREBRAS_API_KEY, OPENAI_API_KEY

    available = {"mistral": bool(MISTRAL_API_KEY), "gemini": bool(GEMINI_API_KEY), "cerebras": bool(CEREBRAS_API_KEY), "openai": bool(OPENAI_API_KEY)}
    fallback_chain = [LLM_PROVIDER] + [m for m in ["mistral", "gemini", "cerebras", "openai"] if m != LLM_PROVIDER and available[m]]
    last_error = ""

    for attempt, model_name in enumerate(fallback_chain):
        model = get_model_by_name(model_name)
        agent = _create_agents(model_override=model)
        try:
            await asyncio.sleep(1)
            result = await Runner.run(
                agent,
                input=user_input,
                session=memory.session,
                max_turns=15,
                error_handlers={
                    "max_turns": lambda _: RunErrorHandlerResult(
                        final_output="I couldn't complete this in time. Try breaking your request into smaller steps.",
                        include_in_history=False,
                    ),
                },
                run_config=run_config,
            )
            await memory.compact_if_needed()
            return result.final_output
        except (RateLimitError, APIStatusError) as e:
            msg = str(e)
            if "Messages with role 'tool'" in msg:
                await memory.delete()
                return "Memory corrupted — deleted and reset. Please try again."
            is_last = attempt == len(fallback_chain) - 1
            prefix = "⚠️ " if is_last else "⚠️ "
            if "429" in msg:
                last_error = f"{prefix}{model_name}: rate limit exceeded"
                continue
            last_error = f"{prefix}{model_name}: {e}"
            continue

    return last_error or "⚠️ All models failed. Try again later."
