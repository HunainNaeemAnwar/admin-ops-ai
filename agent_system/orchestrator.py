import asyncio
import json
import re
from datetime import date
from typing import Optional

import agent_system.provider

from openai import RateLimitError, APIStatusError
from agents import Agent, Runner, function_tool, ModelSettings, GuardrailFunctionOutput, input_guardrail, InputGuardrailTripwireTriggered
from agents.run_config import RunConfig
from agents.run_error_handlers import RunErrorHandlerResult
from config import FIXED_WORKERS, TAX_PERCENTAGE
from agent_system.provider import ACTIVE_MODEL, get_model_by_name
from tools.bus import (
    record_production_batch, mark_worker_absent, mark_all_workers_absent,
    update_production_entry, parse_table, get_date_status,
    get_production_summary, get_catalog, record_rejection,
    record_worker_advance, get_rejection_distribution,
    generate_worker_payslip, generate_payslip_files,
)
from tools.database import (
    get_active_workers, get_all_products, get_worker_id,
    get_total_advances_for_worker_month,
    get_worker_month_production, get_product_id,
    save_payslip,
)
from tools.production_tools import get_product_info
from agent_system.memory_manager import ConversationMemory
from agent_system.cost_tracker import track_usage, format_session_cost


BASE_RUN_CONFIG = RunConfig(tool_not_found_behavior="return_error_to_model")

_memories: dict[str, ConversationMemory] = {}


def _get_memory(session_id: str = "default") -> ConversationMemory:
    if session_id not in _memories:
        _memories[session_id] = ConversationMemory(session_id)
    return _memories[session_id]


# ── Input Guardrail ────────────────────────────────────

MIN_INPUT_LENGTH = 1
MAX_INPUT_LENGTH = 2000


@input_guardrail(name="Input sanitizer", run_in_parallel=False)
async def _input_sanitizer(
    ctx, agent, input_data: str | list
) -> GuardrailFunctionOutput:
    if isinstance(input_data, str):
        sanitized = input_data.strip()
        if not sanitized:
            return GuardrailFunctionOutput(
                tripwire_triggered=True, output_info="Input is empty."
            )
        if len(sanitized) > MAX_INPUT_LENGTH:
            return GuardrailFunctionOutput(
                tripwire_triggered=True,
                output_info=f"Input too long ({len(sanitized)} chars). Max {MAX_INPUT_LENGTH}.",
            )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info="")


GREETING_PATTERN = re.compile(
    r"^(hel+o+|hi|hey|hye|hie|salam|slm|adaab|khushamdeed|good\s*(morning|evening|afternoon|night|day)|sat\s*sri\s*akal|assalam\s*ualaikum|walekum\s*salam)",
    re.IGNORECASE,
)


@input_guardrail(name="Greeting handler", run_in_parallel=False)
async def _greeting_handler(
    ctx, agent, input_data: str | list
) -> GuardrailFunctionOutput:
    if isinstance(input_data, str):
        text = input_data.strip().rstrip("?!.,;:")
        if GREETING_PATTERN.match(text):
            return GuardrailFunctionOutput(
                tripwire_triggered=True,
                output_info="👋 Hello! Main factory accountant hoon. Production entry, reports, payslips, aur advances handle karta hoon. Aap kya karna chahte hain?",
            )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info="")


# ── Instructions per specialist ───────────────────────

PERSONA = """You are a senior factory accountant with 20 years of experience at a manufacturing plant.
You speak Urdu and English mix naturally (Roman Urdu).
You are precise, professional, but friendly with workers.
Financial details are shared only with the father.
You double-check numbers before confirming."""

PRODUCTION_RULES = """<rules>
- Production entry → log_production_tool. Include "date":"YYYY-MM-DD" for past dates (omit for today).
- "sab" / "sab ny" = all workers (Naeem, Kaleem, Akbar, Suny, Sajjad, Irfan, Kashif, Gulmast). Each worker gets same product and quantity.
- Multi-row tables → parse_table_tool
- Worker absent → mark_absent_tool with optional reason (e.g. "Eid", "sick")
- Some present + some absent → batch_daily_update_tool (entries_json + absent_workers in one call)
- Edit entry → update_entry_tool. Pass worker, product_code, date_str, entry_id=0 to auto-lookup.
- Tool warns "already has data" → tell user, ask for confirmation resend
- Multiple workers absent same date → workers="all"
- Worker already absent → report to user, don't retry
- Only record data explicitly stated by user. If information is missing, ask for it.
</rules>"""

REPORTING_RULES = """<rules>
- Status check → get_daily_status_tool
- Summary (daily/weekly/monthly) → get_summary_tool
- Catalog/list → list_catalog_tool
- Email manager (quantities only) → send_report_tool
- Share only quantity-based summaries. Financial data is confidential to father only.
- Tool returns "NO_DATA" → tell user no data exists for that date; do NOT guess or speculate.
</rules>"""

FINANCE_RULES = """<rules>
- Department rejection → log_rejection_tool (equal distribution)
- Worker advance → record_advance_tool
- Generate payslip PDF → generate_payslip_tool
- If month/year not specified, use current month (June 2026)
- Generate immediately. If gross amount is 0 (no production data), inform user and skip payslip.
</rules>"""


HANDOFF_FOOTER = """
You are now handling the user directly. Respond completely in Roman Urdu mixed with English.
Use available tools as needed. After tool execution, explain the result to the user in a friendly way."""


def _production_instructions(ctx, agent) -> str:
    return f"""{PERSONA}

<domain>Production Data Entry</domain>

<context>Workers: {', '.join(FIXED_WORKERS)}
Products: NUT, 10*20, 6*25, 6*30, 10*25 (convert ×/x → *)
Today: {date.today()}</context>

{PRODUCTION_RULES}
{HANDOFF_FOOTER}"""


def _reporting_instructions(ctx, agent) -> str:
    return f"""{PERSONA}

<domain>Production Reporting</domain>

<context>Workers: {', '.join(FIXED_WORKERS)}
Products: NUT, 10*20, 6*25, 6*30, 10*25
Today: {date.today()}</context>

{REPORTING_RULES}
{HANDOFF_FOOTER}"""


def _finance_instructions(ctx, agent) -> str:
    return f"""{PERSONA}

<domain>Finance & Payslips</domain>

<context>Workers: {', '.join(FIXED_WORKERS)}
Products: NUT, 10*20, 6*25, 6*30, 10*25
Today: {date.today()}</context>

{FINANCE_RULES}
{HANDOFF_FOOTER}"""


def _router_instructions(ctx, agent) -> str:
    return f"""{PERSONA}

<domain>Router — classify and delegate</domain>

<context>Workers: {', '.join(FIXED_WORKERS)}
Products: NUT, 10*20, 6*25, 6*30, 10*25
Today: {date.today()}</context>

<rules>
1. Identify intent from user message
2. If enough info present, delegate immediately with sensible defaults (today, current month).
3. Return the specialist's response as-is

Routing:
- Production data entry, tables, absences, edits → delegate_production
- Summary, status, catalog, email reports → delegate_reporting
- Rejections, advances, payslips → delegate_finance
- Greeting → greet. Random/unclear input → politely ask what they need.
- Output says "resend to overwrite" / "already exists" → include in your response

Response format: Always respond in Roman Urdu mixed with English, matching user's language.
</rules>

<examples>
User: hello
You: 👋 Hello! Main factory accountant hoon. Production entry, reports, payslips, aur advances handle karta hoon. Aap kya karna chahte hain?

User: Naeem ne 300 nut kiye
(delegate_production)

User: aj ka status kya hai
(delegate_reporting)

User: Kaleem ki payslip banao
(delegate_finance)

User: 22 June ko Naeem ka data?
(delegate_reporting)
→ ReportingAgent calls get_daily_status_tool(date_str="2026-06-22")

User: aj ka data likha hwa hai
(delegate_reporting)
→ ReportingAgent calls get_daily_status_tool() to show today's status

User: kya haal hai?
Aapka shukriya! Main yahan hoon. Koi production, report, ya payslip ka kaam ho toh bataiye.

User: random gibberish or unclear input
Ask politely: "Bhai, kya karna chahte hain? Production, report, ya payslip?"
</examples>"""


# ── Production Tools ──────────────────────────────────

@function_tool
def log_production_tool(entries_json: str) -> str:
    """Record single or multiple production entries using extracted JSON.

    Use for any number of entries where you can identify worker name, product code, and quantity from natural language.
    Example input: "Naeem made 300 NUT and 150 10*20"
    Example JSON: [{"worker":"Naeem","product_code":"NUT","quantity":300},{"worker":"Naeem","product_code":"10*20","quantity":150}]
    For past dates, include "date":"YYYY-MM-DD" in each entry object.
    "sab" or "sab ny" means all workers from the fixed list.

    Do NOT use for pasted tables — use parse_table_tool instead.

    Args:
        entries_json: JSON array string. Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]
                     Optional field: "date":"YYYY-MM-DD" for past dates.

    Returns:
        Confirmation per entry. May show warning if data already exists.
    """
    try:
        entries = json.loads(entries_json) if isinstance(entries_json, str) else entries_json
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            return "Must be a JSON array"
        for entry in entries:
            date_str = entry.get("date", "")
            if date_str:
                year = int(date_str[:4])
                if year < 2026:
                    return f"⚠️ System records start from 2026. Cannot log data for year {year}."
        return record_production_batch(entries)
    except (json.JSONDecodeError, TypeError):
        return "Invalid JSON format."


@function_tool
def parse_table_tool(worker: str, table_text: str) -> str:
    """Parse a multi-row ASCII production table pasted by the user and record all entries.

    The table must have a DATE column and product columns (NUT, 6*30, 6*25, 10*20, 10*25).
    Handles box-drawing characters (┌─┐└┘├┤│) and plain pipe tables.
    Supports dates in YYYY-MM-DD, MM-DD-YYYY, and DD-MM-YYYY formats.

    Only call this when user pastes a multi-row table. NOT for single-line messages.

    Args:
        worker: Worker name (e.g. 'Naeem')
        table_text: Raw table text as pasted by user, including pipe/border characters

    Returns:
        Per-date results showing what was recorded
    """
    return parse_table(worker, table_text)


@function_tool
def mark_absent_tool(workers: str, date_str: Optional[str] = None, reason: Optional[str] = None) -> str:
    """Mark one or all workers as absent for a given date. Optionally include a reason (e.g. "Eid", "sick", "public holiday").

    For multiple workers absent on the same date, use workers="all".

    Args:
        workers: Worker name (e.g. 'Kaleem') or 'all' to mark all workers absent
        date_str: Date in YYYY-MM-DD format (default: today)
        reason: Optional reason like 'Eid', 'public holiday', 'sick leave'

    Returns:
        Confirmation of which workers were marked absent
    """
    ds = date_str or date.today().isoformat()
    rsn = reason or ""
    if workers.lower() == "all":
        return mark_all_workers_absent(ds, rsn)
    return mark_worker_absent(workers, ds, rsn)


@function_tool
def update_entry_tool(entry_id: int = 0, new_quantity: int = 0, reason: Optional[str] = None,
                       worker: Optional[str] = None, product_code: Optional[str] = None,
                       date_str: Optional[str] = None) -> str:
    """Update the quantity of an existing production entry.

    BEST APPROACH: Provide worker, product_code, and date_str to auto-lookup the correct entry.
    Alternatively, provide entry_id if you already know it from get_daily_status_tool output.

    Args:
        entry_id: Entry ID (e.g. 42). Pass 0 if unknown — use worker/product_code/date_str instead.
        new_quantity: New quantity value (must be positive)
        reason: Optional reason for the change
        worker: Worker name (e.g. 'Naeem') — used for auto-lookup if entry_id is 0
        product_code: Product code (e.g. 'NUT') — used for auto-lookup if entry_id is 0
        date_str: Date YYYY-MM-DD — used for auto-lookup if entry_id is 0

    Returns:
        Old vs new values confirmation
    """
    actual_id = entry_id

    # If entry_id not provided, auto-lookup
    if not actual_id or actual_id <= 0:
        if not worker or not product_code or not date_str:
            return "Give entry_id OR provide worker, product_code, and date_str for lookup."
        from tools.database import get_logs_for_date
        rows = get_logs_for_date(date_str)
        match = None
        for r in rows:
            if r["worker_name"].lower() == worker.lower() and r["product_code"].upper() == product_code.upper():
                match = r
                break
        if not match:
            return f"No {worker} / {product_code} entry found for {date_str}."
        actual_id = match["id"]

    return update_production_entry(actual_id, new_quantity, reason or "")


@function_tool
def batch_daily_update_tool(entries_json: str, absent_workers: Optional[str] = None) -> str:
    """Record production entries AND mark workers absent in a single call.

    Use when some workers are present (producing) and some are absent (chutti/leave).
    For example: "sab ny 300 nut bnaye hain, sunny ki chutti hai"
    → All workers except Suny made 300 NUT, Suny is absent.

    For production-only or absent-only, use the individual tools instead.

    Args:
        entries_json: JSON array of production entries.
            Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]
            Optional "date":"YYYY-MM-DD" for past dates.
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
            results.append(f"[Production]\n{record_production_batch(parsed)}")
    except (json.JSONDecodeError, TypeError) as e:
        results.append(f"[Production] Invalid JSON: {e}")

    if absent_workers:
        try:
            absent_list = json.loads(absent_workers) if isinstance(absent_workers, str) else absent_workers
            if isinstance(absent_list, str):
                absent_list = [absent_list]
            for w in absent_list:
                if isinstance(w, str) and w.strip():
                    results.append(mark_worker_absent(w.strip()))
        except (json.JSONDecodeError, TypeError) as e:
            results.append(f"[Absent] Invalid input: {e}")

    return "\n\n".join(results) if results else "No operations performed."


# ── Reporting Tools ───────────────────────────────────

@function_tool
def get_daily_status_tool(date_str: Optional[str] = None) -> str:
    """Check production data for a specific date. Returns which workers have data, which are absent, and product totals.

    Args:
        date_str: Date in YYYY-MM-DD format ONLY, e.g. "2026-06-22". Do NOT pass natural language. Pass null/None for today.

    Returns:
        Status message with present/absent workers and product totals
    """
    ds = date_str or date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", ds):
        return f"⚠️ Invalid date format: '{date_str}'. Use YYYY-MM-DD, e.g. '2026-06-22'."
    if int(ds[:4]) < 2026:
        return "⚠️ System records start from 2026. Is year ka data exist nahi karta."
    return get_date_status(ds)


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
    today = date.today()
    y = year or today.year
    if y < 2026:
        return "⚠️ System records start from 2026. Please select year >= 2026."
    return get_production_summary(period, y, month or today.month, day or today.day)


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
    return send_summary(period, year or today.year, month or today.month, day or today.day)


@function_tool
def list_catalog_tool() -> str:
    """List all workers, products with rates, and today's production status.

    Returns:
        Catalog info including worker list, product rates, and current date
    """
    return get_catalog()


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
    return record_rejection(year, month, product_code, total_qty, excluded)


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
    return record_worker_advance(worker, amount, year, month, description or "")


@function_tool
def generate_payslip_tool(year: int, month: int, worker: Optional[str] = None) -> str:
    """Generate PDF payslip for one worker or all workers for a given month.
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
    if y < 2026:
        return "⚠️ Payslips only available from 2026 onwards."

    distribution = get_rejection_distribution(y, m)

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
        for code, qty in product_totals.items():
            product = get_product_info(code)
            if product:
                gross_total += qty * product["rate"]

        rejection_value = 0
        for dist in distribution:
            w_share = dist["distribution"].get(w, 0)
            product = get_product_info(dist["product_code"])
            if product:
                rejection_value += w_share * product["rate"]

        advance_total = get_total_advances_for_worker_month(wid, y, m)

        tax_amount = round(gross_total * TAX_PERCENTAGE / 100, 2)
        net_payable = round(gross_total - rejection_value - advance_total - tax_amount, 2)

        save_payslip(wid, y, m, gross_total, tax_amount, rejection_value, advance_total, net_payable)
        pdf_path, xls_path = generate_payslip_files(w, y, m)

        results.append(
            f"  {w}: Gross Rs {gross_total:,.2f}, "
            f"Reject Rs {rejection_value:,.2f}, "
            f"Advance Rs {advance_total:,.2f}, "
            f"Tax Rs {tax_amount:,.2f}, "
            f"Net Rs {net_payable:,.2f}\n"
            f"    PDF: {pdf_path}\n    Excel: {xls_path}"
        )

    if not results:
        return "No payslips generated."
    return f"Payslips for {y}-{m:02d}:\n" + "\n".join(results)


# ── Agent factory ─────────────────────────────────────

def _create_agents(router_model_override=None, specialist_model_override=None):
    s_model = specialist_model_override or router_model_override or ACTIVE_MODEL
    r_model = router_model_override or ACTIVE_MODEL
    base_settings = ModelSettings(
        temperature=0.5,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=True,
    )

    production_agent = Agent(
        name="ProductionAgent",
        instructions=_production_instructions,
        model=s_model,
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
        model=s_model,
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
        model=s_model,
        model_settings=base_settings,
        tools=[
            log_rejection_tool,
            record_advance_tool,
            generate_payslip_tool,
        ],
    )

    router_settings = ModelSettings(
        temperature=0.3,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=False,
    )
    router = Agent(
        name="Router",
        instructions=_router_instructions,
        model=r_model,
        model_settings=router_settings,
        input_guardrails=[_greeting_handler, _input_sanitizer],
        tools=[
            production_agent.as_tool(
                tool_name="delegate_production",
                tool_description="Production data entry, tables, absences, and entry edits.",
            ),
            reporting_agent.as_tool(
                tool_name="delegate_reporting",
                tool_description="Production summary, daily status, catalog listing, and email reports.",
            ),
            finance_agent.as_tool(
                tool_name="delegate_finance",
                tool_description="Payslip generation, advance payments, and rejection recording.",
            ),
        ],
    )
    return router


# ── Chat ──────────────────────────────────────────────

async def chat(user_input: str, session_id: str = "default") -> str:
    memory = _get_memory(session_id)
    await memory.cleanup()

    from config import LLM_PROVIDER
    from agent_system.provider import _models as all_models

    primary = LLM_PROVIDER if LLM_PROVIDER in all_models else "gemini"
    fallback_chain = ["mistral", "gemini", "gemini-3.1", "cerebras"]
    fallback_chain = [m for m in fallback_chain if m in all_models]
    if primary in fallback_chain:
        fallback_chain.remove(primary)
    fallback_chain.insert(0, primary)
    if not fallback_chain:
        fallback_chain = ["mistral"]
    last_error = ""

    for attempt, model_name in enumerate(fallback_chain):
        specialist_model = get_model_by_name(model_name)
        router_model = specialist_model
        agent = _create_agents(
            router_model_override=router_model,
            specialist_model_override=specialist_model,
        )
        try:
            result = await asyncio.wait_for(
                Runner.run(
                    agent,
                    input=user_input,
                    session=memory.session,
                    max_turns=10,
                    error_handlers={
                        "max_turns": lambda _: RunErrorHandlerResult(
                            final_output="Mujhe is request ko complete karne mein zyada time lag raha hai. Please chhotee request mein tod dein.",
                            include_in_history=False,
                        ),
                    },
                    run_config=BASE_RUN_CONFIG,
                ),
                timeout=30,
            )
            track_usage(session_id, model_name, user_input, str(result.final_output)[:200])
            await memory.compact_if_needed()
            return result.final_output
        except asyncio.TimeoutError:
            return "⚠️ Server busy — please thodi der baad try karein."
        except InputGuardrailTripwireTriggered as e:
            msg = e.guardrail_result.output.output_info or "OK"
            await memory.session.add_items([{"role": "assistant", "content": msg}])
            return msg
        except (RateLimitError, APIStatusError) as e:
            msg = str(e)
            if "Messages with role 'tool'" in msg:
                await memory.delete()
                try:
                    result = await asyncio.wait_for(
                        Runner.run(
                            agent,
                            input=user_input,
                            session=_get_memory(session_id).session,
                            max_turns=10,
                            run_config=BASE_RUN_CONFIG,
                        ),
                        timeout=30,
                    )
                    track_usage(session_id, model_name, user_input, str(result.final_output)[:200])
                    await _get_memory(session_id).compact_if_needed()
                    return result.final_output
                except Exception:
                    return "Memory corrupted — delete kar di. Dobara try karein."
            is_last = attempt == len(fallback_chain) - 1
            prefix = "⚠️ " if is_last else "⚠️ "
            if "429" in msg:
                last_error = f"{prefix}{model_name}: rate limit exceeded"
                continue
            last_error = f"{prefix}{model_name}: {e}"
            continue

    return last_error or "⚠️ Sab models fail ho gaye. Baad mein try karein."


# ── Streaming ─────────────────────────────────────────

async def stream_chat(user_input: str, session_id: str = "default"):
    """Generator that yields SSE-formatted chunks from streaming agent response."""
    memory = _get_memory(session_id)
    await memory.cleanup()

    from config import LLM_PROVIDER
    from agent_system.provider import _models as all_models

    primary = LLM_PROVIDER if LLM_PROVIDER in all_models else "gemini"
    fallback_chain = ["mistral", "gemini", "gemini-3.1", "cerebras"]
    fallback_chain = [m for m in fallback_chain if m in all_models]
    if primary in fallback_chain:
        fallback_chain.remove(primary)
    fallback_chain.insert(0, primary)
    if not fallback_chain:
        fallback_chain = ["mistral"]

    for attempt, model_name in enumerate(fallback_chain):
        specialist_model = get_model_by_name(model_name)
        router_model = specialist_model
        agent = _create_agents(
            router_model_override=router_model,
            specialist_model_override=specialist_model,
        )
        try:
            result = Runner.run_streamed(
                agent,
                input=user_input,
                session=memory.session,
                max_turns=10,
                run_config=BASE_RUN_CONFIG,
            )
            async for event in result.stream_events():
                if event.type == "raw_response_event" and hasattr(event.data, "delta"):
                    delta = event.data.delta
                    if delta and isinstance(delta, str):
                        yield f"data: {delta}\n\n"

            final = await result.result()
            yield f"data: [DONE]\n\n"
            track_usage(session_id, model_name, user_input, str(final.final_output)[:200])
            await memory.compact_if_needed()
            return
        except InputGuardrailTripwireTriggered as e:
            msg = e.guardrail_result.output.output_info or "OK"
            await memory.session.add_items([{"role": "assistant", "content": msg}])
            yield f"data: {msg}\n\ndata: [DONE]\n\n"
            return
        except (RateLimitError, APIStatusError) as e:
            msg = str(e)
            if "Messages with role 'tool'" in msg:
                await memory.delete()
                yield f"data: Memory corrupted — delete kar di. Dobara try karein.\n\ndata: [DONE]\n\n"
                return
            if attempt == len(fallback_chain) - 1:
                yield f"data: ⚠️ {model_name}: {e}\n\ndata: [DONE]\n\n"
                return
            continue

    yield f"data: ⚠️ Sab models fail ho gaye.\n\ndata: [DONE]\n\n"
