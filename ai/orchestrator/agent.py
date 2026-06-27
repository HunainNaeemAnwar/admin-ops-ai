import asyncio
import json
import re
from datetime import date
from typing import Optional

import ai.provider

from openai import RateLimitError, APIStatusError
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, function_tool, handoff, ModelSettings, GuardrailFunctionOutput, input_guardrail, InputGuardrailTripwireTriggered, output_guardrail, ToolGuardrailFunctionOutput, tool_output_guardrail
from agents.run_config import RunConfig
from agents.run_error_handlers import RunErrorHandlerResult
from config import FIXED_WORKERS, TAX_PERCENTAGE, FALLBACK_MODELS, ROUTER_MODEL
from ai.provider import ACTIVE_MODEL, get_model_by_name
from tools.bus import (
    record_production_batch, mark_worker_absent, mark_all_workers_absent,
    update_production_entry, parse_table, get_date_status,
    get_production_summary, get_catalog, record_rejection,
    record_worker_advance, get_rejection_distribution,
)
from tools.database import (
    get_active_workers, get_all_products, get_worker_id,
    get_total_advances_for_worker_month,
    get_worker_month_production, get_product_id,
    get_payslip, save_payslip,
)
from tools.production_tools import get_product_info
from tools.payslip_tools import generate_pdf_payslip
from ai.memory import ConversationMemory
from ai.cost_tracker import track_usage, format_session_cost


BASE_RUN_CONFIG = RunConfig(tool_not_found_behavior="return_error_to_model")

_memories: dict[str, ConversationMemory] = {}
_memory_lock = asyncio.Lock()


async def _get_memory(session_id: str = "default") -> ConversationMemory:
    async with _memory_lock:
        if session_id not in _memories:
            _memories[session_id] = ConversationMemory(session_id)
        return _memories[session_id]


async def _remove_memory(session_id: str):
    memory = _memories.pop(session_id, None)
    if memory:
        await memory.delete()
    ConversationMemory.delete_from_db(session_id)


async def _forget_memory(session_id: str):
    """Clear SDK session cache without touching chat_messages table."""
    _memories.pop(session_id, None)
    m = ConversationMemory(session_id)
    await m.delete()


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


# ── Output Guardrails ──────────────────────────────────

FINANCIAL_KEYWORDS = re.compile(
    r"(Rs\s*[\d,]+\.?\d*|salary|wage|payslip|tax|deduction|net\s*payable|gross|rate\s*per\s*piece)",
    re.IGNORECASE,
)


@output_guardrail(name="Financial data protector")
async def _finance_output_guardrail(
    ctx, agent, output: str
) -> GuardrailFunctionOutput:
    """Prevent financial data leakage from non-finance agents."""
    agent_name = getattr(agent, "name", "")
    if agent_name in ("FinanceAgent", "Router"):
        return GuardrailFunctionOutput(tripwire_triggered=False, output_info="")
    if FINANCIAL_KEYWORDS.search(output):
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info="Share the quantity summary without financial breakdown.",
        )
    return GuardrailFunctionOutput(tripwire_triggered=False, output_info="")


@tool_output_guardrail
async def _production_tool_output_guardrail(data) -> ToolGuardrailFunctionOutput:
    """Ensure production tool output contains confirmation data."""
    text = str(data.output or "")
    if "Invalid" in text or "error" in text.lower():
        return ToolGuardrailFunctionOutput.reject_content(
            "Entry failed — ask user for corrected data."
        )
    return ToolGuardrailFunctionOutput.allow()


# ── Instructions per specialist ───────────────────────

PERSONA = """You are a factory accountant speaking Roman Urdu/English.
Complete requests naturally without explaining your process or internal workings."""

WORKER_LIST = ', '.join(FIXED_WORKERS)
CONTEXT_BLOCK = f"""Workers: {WORKER_LIST}
Products: NUT, 10*20, 6*25, 6*30, 10*25 (convert ×/x → *)
Today: {date.today()}"""


def _production_instructions(ctx, agent) -> str:
    return f"""
<role>
You record production data by calling tools. Text alone does not save anything — 
you must call the appropriate tool to persist every entry.
</role>

<context>
Workers: {WORKER_LIST}
Products: NUT, 10*20, 6*25, 6*30, 10*25 (convert ×/x → *)
Today: {date.today()}
</context>

<tools>
- log_production_tool: JSON array of entries. "sab" = all 8 workers. Optional "date":"YYYY-MM-DD".
- batch_daily_update_tool: Production entries + absences in one call.
- parse_table_tool: Pipe/border table for one worker across multiple dates.
- mark_absent_tool: Single worker or "all". Optional reason + date.
- update_entry_tool: Change quantity. Provide worker+product+date or entry_id.
</tools>

  <rules>
- Call the tool first, then confirm with a short message.
- Duplicate exists? Say so. User resends same data → overwrite.
- Use "sab" when all 8 workers have same product+quantity.
- For mixed data (different quantities per worker, some absent), build one JSON array and call once.
- Ambiguous product codes like 627/6*27/6 27 → ask "6*25 ya 6*30?"
- Past dates: add "date":"YYYY-MM-DD" in entry JSON.
- Only record what is explicitly stated.
- If a worker is excluded ("k ilawa", "except", "baqi", "sivay"), record the included workers' entries first, then ask about the excluded worker's status before marking anything.
- Do not record 0 for the excluded worker. Do not guess. Ask first.
- Format confirmations as markdown: one row per worker in a small table or bullet list.
</rules>

<examples>
User: Naeem ne 300 nut kiye
→ Call log_production_tool
Answer: Naeem ka 300 NUT record kar diya ✅

User: sab ny 300 nut kiye, Sunny chutti par hai
→ Call batch_daily_update_tool(7×300 NUT, absent=["Sunny"])
Answer: 7 workers ne 300 NUT kiye. Sunny absent ✅

User: sab kay 300 nut hain Kaleem k ilawa
→ Call log_production_tool for 7 workers (300 NUT each)
Answer: 7 workers ka 300 NUT record kar diya ✅. Kaleem ka kya hai? Absent tha ya chutti thi?
  User: chutti thi
  → Call mark_absent_tool("Kaleem")
  Answer: Kaleem absent ✅

User: aj ka data likho naeem k 3000 nut kaaleem aur baqiyon k 2000 nut aur naeem k ilawa sab nay 3000 10 20 bnaya tha aur 400 625
→ Build complete JSON for all entries, call log_production_tool
Answer: Naeem: 3000 NUT ✅ Kaleem: 2000 NUT ✅ baki 6: 2000 NUT each ✅. Naeem k ilawa sab: 3000 10*20 + 400 6*25 ✅

User: Naeem ne 300 nut kiye (same data again)
→ Tool returns "already exists"
Answer: Naeem ke paas pehle se 300 NUT hai. Dobara bhejain to overwrite.

User: Sunny ki chutti hai
→ Call mark_absent_tool("Sunny")
Answer: Sunny ko aaj absent mark kar diya ✅

User: 20 June ko Naeem ka 250 kar do
→ Call update_entry_tool or log_production_tool with date
Answer: 20 June ka Naeem ka NUT 250 kar diya ✅
</examples>"""


def _reporting_instructions(ctx, agent) -> str:
    return f"""
<role>
You check and share production data. Call the correct tool to retrieve real data — 
never invent numbers.
</role>

<context>
Workers: {WORKER_LIST}
Products: NUT, 10*20, 6*25, 6*30, 10*25
Today: {date.today()}
</context>

<tools>
- get_daily_status_tool: Present/absent workers + product totals for a date.
- get_summary_tool: Daily/weekly/monthly per-worker quantities.
- send_report_tool: Email quantity-only report to manager.
- list_catalog_tool: Workers, product rates, today's status.
</tools>

<rules>
- Call the tool to get data. Never guess numbers.
- "email" → send_report_tool.
- "status" / "check" / "kya hai" → get_daily_status_tool or get_summary_tool.
- "catalog" / "workers" / "products" → list_catalog_tool.
- Format all output as markdown tables when showing worker×product data.
  Use pipe tables: | Worker | NUT | 10*20 | ... |
- Keep response concise — table + summary line.
</rules>

<examples>
User: aj ka status kya hai
→ Call get_daily_status_tool
Answer: | Worker     | NUT  | Status |
           |------------|------|--------|
           | Naeem      | 300  | ✅     |
           | Kaleem     | 250  | ✅     |
           | Akbar      | 0    | ABSENT |
           Total: 550 pieces. 1 absent.

User: manager ko email bhej do
→ Call send_report_tool
Answer: Manager ko email bhej diya ✅

User: catalog dikhao
→ Call list_catalog_tool
Answer: | Worker  | Product | Rate    |
           |---------|---------|---------|
           | Naeem   | NUT     | Rs 0.50 |

User: monthly summary do June 2026
→ Call get_summary_tool("monthly", 2026, 6)
Answer: | Worker  | NUT    | 10*20  | 6*25   |
           |---------|--------|--------|--------|
           | Naeem   | 5,000  | 750    | 3,000  |
           | Kaleem  | 5,000  | 750    | 3,000  |
           | Total   | 10,000 | 1,500  | 6,000  |
           June 2026 total: 17,500 pieces.
</examples>"""


def _finance_instructions(ctx, agent) -> str:
    return f"""
<role>
You handle payslips, advances, and rejections. Call the correct tool — 
text alone does not generate payslips or record transactions.
</role>

<context>
Workers: {WORKER_LIST}
Products: NUT, 10*20, 6*25, 6*30, 10*25
Default month: {date.today().strftime("%B %Y")}
</context>

<tools>
- log_rejection_tool: Department rejection, equal distribution, exclude some workers.
- record_advance_tool: Advance payment for a worker in a month.
- generate_payslip_tool: PDF payslip, single worker or all workers.
</tools>

<rules>
- Call the tool to perform operations. Text alone does nothing.
- Default to current month if user does not specify.
- No production data for a worker → say so.
- Unknown worker name → "Yeh worker list main nahi hai. Sahi naam batao."
</rules>

<examples>
User: Kaleem ki payslip banao June 2026
→ Call generate_payslip_tool(2026, 6, "Kaleem")
Answer: Kaleem ki June payslip ready hai ✅

User: Naeem ko 2000 advance do
→ Call record_advance_tool("Naeem", 2000, 2026, 6)
Answer: Naeem ka Rs 2,000 advance June ke liye record kar diya ✅

User: NUT ki rejection 50 hai
→ Call log_rejection_tool(2026, 6, "NUT", 50)
Answer: 50 NUT rejection record ki. Har worker par 6 pieces.

User: Kaleem ki payslip banao (no data)
→ Tool returns no production data
Answer: Kaleem ka June main koi production data nahi mila.

User: unknown worker ka advance
→ Tool returns unknown
Answer: Yeh worker list main nahi hai. Sahi naam batao.
</examples>"""


def _router_instructions(ctx, agent) -> str:
    return f"""
<role>
You are a factory accountant. Understand what the user wants and hand off to the correct specialist.
Never answer production/reporting/finance questions directly — always hand off.
</role>

<context>
Workers: {WORKER_LIST}
Products: NUT, 10*20, 6*25, 6*30, 10*25 (convert ×/x → *)
Today: {date.today()}
</context>

<handoffs>
- delegate_production  → production entry, absences, tables, entry edits
- delegate_reporting   → daily status, summaries, catalog, email reports
- delegate_finance     → payslips, advances, rejections
</handoffs>

<rules>
- Greeting → respond naturally.
- If user seems dissatisfied or confused, ask a specific clarifying question based on recent context — do not default to a generic response.
- Format all data output as markdown tables when presenting numbers.
- Keep responses concise.
</rules>

<examples>
User: Naeem ne 300 nut kiye          → delegate_production
User: aj ka status kya hai             → delegate_reporting
User: Kaleem ki payslip banao           → delegate_finance
User: manager ko email bhej do          → delegate_reporting
User: kya haal hai                      → "Main theek hoon! Koi kaam hai?"
User: yeh system kaise kaam karta hai   → "Production data record kar sakte hain, reports dekh sakte hain, payslips generate kar sakte hain. Kya karna chahte hain?"
User: nahi yeh nahi / kuch aur          → Acknowledge confusion, reference last few messages, ask specific question.
</examples>"""


# ── Production Tools ──────────────────────────────────

@function_tool
async def log_production_tool(entries_json: str) -> str:
    """Record production entries from JSON data.

    Accepts worker name, product code, quantity, and optional date.
    "sab" / "sab ny" = all 8 workers with same product/quantity.
    Past dates: include "date":"YYYY-MM-DD" in each entry.

    Args:
        entries_json: JSON array. Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]

    Returns:
        Confirmation per entry.
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
        return await record_production_batch(entries)
    except (json.JSONDecodeError, TypeError):
        return "Invalid JSON format."


@function_tool
def parse_table_tool(worker: str, table_text: str) -> str:
    """Parse a multi-row ASCII production table and record all entries.

    Handles box-drawing characters and pipe tables.
    Supports YYYY-MM-DD, MM-DD-YYYY, and DD-MM-YYYY date formats.

    Args:
        worker: Worker name (e.g. 'Naeem')
        table_text: Raw table text including pipe/border characters

    Returns:
        Per-date confirmation of recorded entries.
    """
    return parse_table(worker, table_text)


@function_tool
def mark_absent_tool(workers: str, date_str: Optional[str] = None, reason: Optional[str] = None) -> str:
    """Mark one or all workers absent for a date.

    Args:
        workers: Worker name or 'all' for everyone
        date_str: Date YYYY-MM-DD (default: today)
        reason: Reason like 'Eid', 'sick'

    Returns:
        Confirmation message.
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
    """Update an existing production entry.

    Provide worker + product_code + date_str for auto-lookup, or entry_id directly.

    Args:
        entry_id: Entry ID (0 = auto-lookup via worker/product_code/date_str)
        new_quantity: New quantity (must be positive)
        reason: Reason for change
        worker: Worker name for auto-lookup
        product_code: Product code for auto-lookup
        date_str: Date YYYY-MM-DD for auto-lookup

    Returns:
        Old vs new confirmation.
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
async def batch_daily_update_tool(entries_json: str, absent_workers: Optional[str] = None) -> str:
    """Record production and mark absences in one call.

    Args:
        entries_json: JSON array. Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]
        absent_workers: JSON array of worker names to mark absent, or null.

    Returns:
        Combined results.
    """
    results = []
    try:
        parsed = json.loads(entries_json) if isinstance(entries_json, str) else entries_json
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            results.append("[Production] Invalid: must be an array")
        else:
            results.append(f"[Production]\n{await record_production_batch(parsed)}")
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
    """Check production data for a date. Shows present/absent workers and totals.

    Args:
        date_str: Date YYYY-MM-DD (default: today).

    Returns:
        Status with present/absent workers and product totals.
    """
    ds = date_str or date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", ds):
        return f"⚠️ Invalid date format: '{date_str}'. Use YYYY-MM-DD, e.g. '2026-06-22'."
    if int(ds[:4]) < 2026:
        return "⚠️ System records start from 2026. Is year ka data exist nahi karta."
    return get_date_status(ds)


@function_tool
def get_summary_tool(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Production summary for a period.

    Args:
        period: 'daily', 'weekly', or 'monthly'
        year: Year (default: current)
        month: Month 1-12 (default: current)
        day: Day 1-31 (default: today)

    Returns:
        Summary with product totals per worker.
    """
    today = date.today()
    y = year or today.year
    if y < 2026:
        return "⚠️ System records start from 2026. Please select year >= 2026."
    return get_production_summary(period, y, month or today.month, day or today.day)


@function_tool
def send_report_tool(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Email production summary to the manager.

    Args:
        period: 'daily', 'weekly', or 'monthly'
        year: Year (default: current)
        month: Month 1-12 (default: current)
        day: Day 1-31 (default: today)

    Returns:
        Delivery status.
    """
    from tools.email_tools import send_summary
    today = date.today()
    return send_summary(period, year or today.year, month or today.month, day or today.day)


@function_tool
def list_catalog_tool() -> str:
    """List all workers, products, and today's status.

    Returns:
        Worker list, product rates, and current date.
    """
    return get_catalog()


# ── Finance Tools ─────────────────────────────────────

@function_tool
def log_rejection_tool(year: int, month: int, product_code: str, total_qty: int, excluded_workers: Optional[str] = None) -> str:
    """Record department-level rejection for a month.

    Rejection is equally distributed among eligible workers.

    Args:
        year: Year (e.g. 2026)
        month: Month 1-12
        product_code: NUT, 10*20, 6*25, 6*30, or 10*25
        total_qty: Total rejected pieces
        excluded_workers: JSON array of workers to exclude, or null

    Returns:
        Distribution confirmation.
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
    """Record advance payment to a worker.

    Args:
        worker: Worker name
        amount: Amount in rupees
        year: Year
        month: Month 1-12
        description: Optional reason

    Returns:
        Confirmation with monthly total.
    """
    return record_worker_advance(worker, amount, year, month, description or "")


@function_tool
def generate_payslip_tool(year: int, month: int, worker: Optional[str] = None) -> str:
    """Generate PDF payslip for a worker or all workers.

    Args:
        year: Year
        month: Month 1-12
        worker: Worker name, or null/empty for all workers

    Returns:
        Confirmation message.
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
        tax_total = 0.0
        for code, qty in product_totals.items():
            product = get_product_info(code)
            if product:
                val = qty * product["rate"]
                gross_total += val
                tax_pct = product["tax_pct"] if product["tax_pct"] > 0 else TAX_PERCENTAGE
                tax_total += round(val * tax_pct / 100, 2)

        rejection_value = 0
        for dist in distribution:
            w_share = dist["distribution"].get(w, 0)
            product = get_product_info(dist["product_code"])
            if product:
                rejection_value += w_share * product["rate"]

        advance_total = get_total_advances_for_worker_month(wid, y, m)

        tax_amount = round(tax_total, 2)
        net_payable = round(gross_total - rejection_value - advance_total - tax_amount, 2)

        existing_payslip = get_payslip(wid, y, m)
        if existing_payslip:
            results.append(
                f"  ⚠️ {w}: {y}-{m:02d} payslip already exists (Rs {existing_payslip['net_payable']:,.0f}). "
                f"Regenerate to overwrite."
            )
            continue

        save_payslip(wid, y, m, gross_total, tax_amount, rejection_value, advance_total, net_payable)
        generate_pdf_payslip(w, y, m)

        results.append(
            f"  {w}: {y}-{m:02d} payslip ready — "
            f"Gross Rs {gross_total:,.0f}, "
            f"Net Rs {net_payable:,.0f}"
        )

    if not results:
        return "No payslips generated."
    return f"Payslips for {y}-{m:02d}:\n" + "\n".join(results)


# ── Agent factory ─────────────────────────────────────

def _create_agents(router_model_override=None, specialist_model_override=None):
    s_model = specialist_model_override or router_model_override or ACTIVE_MODEL
    r_model = router_model_override or ACTIVE_MODEL

    prod_settings = ModelSettings(
        temperature=0.2,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=True,
    )
    report_settings = ModelSettings(
        temperature=0.3,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=True,
    )
    finance_settings = ModelSettings(
        temperature=0.3,
        top_p=0.9,
        max_tokens=2000,
        parallel_tool_calls=True,
    )

    production_agent = Agent(
        name="ProductionAgent",
        instructions=_production_instructions,
        model=s_model,
        model_settings=prod_settings,
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
        model_settings=report_settings,
        output_guardrails=[_finance_output_guardrail],
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
        model_settings=finance_settings,
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
        output_guardrails=[_finance_output_guardrail],
        handoffs=[
            handoff(
                production_agent,
                tool_name_override="delegate_production",
                tool_description_override="Production data entry, tables, absences, and entry edits.",
            ),
            handoff(
                reporting_agent,
                tool_name_override="delegate_reporting",
                tool_description_override="Production summary, daily status, catalog listing, and email reports.",
            ),
            handoff(
                finance_agent,
                tool_name_override="delegate_finance",
                tool_description_override="Payslip generation, advance payments, and rejection recording.",
            ),
        ],
    )
    return router


# ── Chat ──────────────────────────────────────────────

async def chat(user_input: str, session_id: str = "default") -> str:
    memory = await _get_memory(session_id)
    await memory.cleanup()

    existing = await memory.session.get_items()

    if not existing:
        saved = ConversationMemory.load_from_db(session_id)
        if saved:
            await memory.session.add_items(saved)
            existing = saved

    from ai.provider import _models as all_models

    fallback_chain = [m for m in FALLBACK_MODELS if m in all_models]
    if not fallback_chain:
        fallback_chain = list(all_models.keys())[:1] or ["mistral"]
    last_error = ""

    for attempt, model_name in enumerate(fallback_chain):
        specialist_model = get_model_by_name(model_name)
        if ROUTER_MODEL and ROUTER_MODEL in all_models:
            router_model = get_model_by_name(ROUTER_MODEL)
        else:
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
                    max_turns=15,
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
            items = await memory.session.get_items()
            ConversationMemory.save_to_db(session_id, items)
            return result.final_output
        except asyncio.TimeoutError:
            return "⚠️ Server busy — please thodi der baad try karein."
        except InputGuardrailTripwireTriggered as e:
            msg = e.guardrail_result.output.output_info or "OK"
            await memory.session.add_items([{"role": "assistant", "content": msg}])
            items = await memory.session.get_items()
            ConversationMemory.save_to_db(session_id, items)
            return msg
        except (RateLimitError, APIStatusError) as e:
            msg = str(e)
            if "Messages with role 'tool'" in msg:
                _memories.pop(session_id, None)
                await memory.delete()
                ConversationMemory.delete_from_db(session_id)
                try:
                    result = await asyncio.wait_for(
                        Runner.run(
                            agent,
                            input=user_input,
                            session=(await _get_memory(session_id)).session,
                            max_turns=15,
                            run_config=BASE_RUN_CONFIG,
                        ),
                        timeout=30,
                    )
                    track_usage(session_id, model_name, user_input, str(result.final_output)[:200])
                    mem = await _get_memory(session_id)
                    await mem.compact_if_needed()
                    items = await mem.session.get_items()
                    ConversationMemory.save_to_db(session_id, items)
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
    memory = await _get_memory(session_id)
    await memory.cleanup()

    existing = await memory.session.get_items()

    if not existing:
        saved = ConversationMemory.load_from_db(session_id)
        if saved:
            await memory.session.add_items(saved)

    from ai.provider import _models as all_models

    fallback_chain = [m for m in FALLBACK_MODELS if m in all_models]
    if not fallback_chain:
        fallback_chain = list(all_models.keys())[:1] or ["mistral"]

    for attempt, model_name in enumerate(fallback_chain):
        specialist_model = get_model_by_name(model_name)
        if ROUTER_MODEL and ROUTER_MODEL in all_models:
            router_model = get_model_by_name(ROUTER_MODEL)
        else:
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
                max_turns=15,
                run_config=BASE_RUN_CONFIG,
            )
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    if event.data.delta:
                        yield f"data: {event.data.delta}\n\n"

            yield f"data: [DONE]\n\n"
            track_usage(session_id, model_name, user_input, str(result.final_output)[:200])
            await memory.compact_if_needed()
            items = await memory.session.get_items()
            ConversationMemory.save_to_db(session_id, items)
            return
        except InputGuardrailTripwireTriggered as e:
            msg = e.guardrail_result.output.output_info or "OK"
            await memory.session.add_items([{"role": "assistant", "content": msg}])
            items = await memory.session.get_items()
            ConversationMemory.save_to_db(session_id, items)
            yield f"data: {msg}\n\ndata: [DONE]\n\n"
            return
        except (RateLimitError, APIStatusError) as e:
            msg = str(e)
            if "Messages with role 'tool'" in msg:
                _memories.pop(session_id, None)
                await memory.delete()
                ConversationMemory.delete_from_db(session_id)
                yield f"data: Memory corrupted — delete kar di. Dobara try karein.\n\ndata: [DONE]\n\n"
                return
            if attempt == len(fallback_chain) - 1:
                yield f"data: ⚠️ {model_name}: {e}\n\ndata: [DONE]\n\n"
                return
            continue

    yield f"data: ⚠️ Sab models fail ho gaye.\n\ndata: [DONE]\n\n"
