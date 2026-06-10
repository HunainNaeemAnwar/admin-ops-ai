import asyncio
from datetime import date
from typing import Optional

import agent_system.provider

from agents import Agent, Runner, function_tool
from config import GEMINI_MODEL
from tools.excel_tools import (
    load_product_catalog, get_all_workers, get_worker_entries, read_month_entries,
    append_work_entry, lookup_product, has_today_entries, FIXED_WORKERS,
)
from tools.calc_tools import (
    calc_piece_rate, calc_daily_summary, calc_monthly_summary, calc_worker_payslip,
)
from tools.email_tools import send_daily_summary
from tools.payslip_tools import generate_pdf_payslip, generate_excel_payslip
from agent_system.data_extractor import extract_from_text


@function_tool
async def record_work_tool(worker: str, product_code: str, quantity: int) -> str:
    """Record a daily work entry for a worker. Use this when a worker has completed pieces of a specific product.

    Args:
        worker: Worker's name (e.g., 'Ahmed', 'Ali')
        product_code: Product code from catalog (e.g., 'BOLT-10x20', 'NUT-STD', 'BOLT-6x25')
        quantity: Number of pieces completed (must be positive)

    Returns:
        Confirmation with calculated gross, tax, and net amounts
    """
    result = calc_piece_rate(product_code, quantity)
    if "error" in result:
        products = load_product_catalog()
        available = ", ".join(p["product_code"] for p in products)
        return f"{result['error']}. Available: {available}"
    append_work_entry(
        worker=worker, product_code=result["product_code"],
        description=result["description"], quantity=result["quantity"],
        rate=result["rate"], gross=result["gross"],
        tax_pct=result["tax_pct"], tax_amt=result["tax_amt"], net=result["net"],
    )
    return (
        f"Recorded: {worker} - {result['quantity']}x{result['product_code']} "
        f"(Gross Rs {result['gross']:,.2f}, Tax Rs {result['tax_amt']:,.2f}, Net Rs {result['net']:,.2f})"
    )


@function_tool
async def record_work_from_text_tool(text: str) -> str:
    """Record work entries from natural language text. Use this when someone describes work in plain language.

    Args:
        text: Natural language description of work (e.g., 'Ahmed ne 50 bolt 10*20 aur 30 nuts buff kiye')

    Returns:
        Summary of all recorded entries
    """
    parsed = await extract_from_text(text)
    results = []
    total_net = 0.0
    for prod in parsed.products:
        result = calc_piece_rate(prod.product_code, prod.quantity)
        if "error" in result:
            results.append(f"  {prod.product_code}: {result['error']}")
            continue
        append_work_entry(
            worker=parsed.worker, product_code=result["product_code"],
            description=result["description"], quantity=result["quantity"],
            rate=result["rate"], gross=result["gross"],
            tax_pct=result["tax_pct"], tax_amt=result["tax_amt"], net=result["net"],
        )
        results.append(f"  {result['quantity']}x{result['product_code']} -> Net Rs {result['net']:,.2f}")
        total_net += result["net"]
    return f"Recorded {len(results)} entries for {parsed.worker}:\n" + "\n".join(results) + f"\nTotal Net: Rs {total_net:,.2f}"


@function_tool
def get_daily_total_tool(year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Get the total production amount for a specific day.

    Args:
        year: Year (default: current)
        month: Month 1-12 (default: current)
        day: Day 1-31 (default: today)

    Returns:
        Daily summary with totals
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day
    summary = calc_daily_summary(y, m, d)
    return (
        f"Daily Summary - {summary['date']}\n"
        f"Workers: {summary['workers_count']} | Entries: {summary['entries_count']}\n"
        f"Total Pieces: {summary['total_pieces']}\n"
        f"Gross: Rs {summary['total_gross']:,.2f} | Tax: Rs {summary['total_tax']:,.2f}\n"
        f"Net Total: Rs {summary['total_net']:,.2f}"
    )


@function_tool
def get_monthly_summary_tool(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Get complete monthly production summary with per-worker breakdown.

    Args:
        year: Year (default: current)
        month: Month 1-12 (default: current)

    Returns:
        Monthly report with totals and worker breakdown
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    summary = calc_monthly_summary(y, m)
    lines = [
        f"Monthly Summary - {y}-{m:02d}",
        f"Workers: {summary['total_workers']} | Entries: {summary['total_entries']}",
        f"Pieces: {summary['total_pieces']} | Gross: Rs {summary['total_gross']:,.2f}",
        f"Tax: Rs {summary['total_tax']:,.2f} | Net: Rs {summary['total_net']:,.2f}",
        "",
        "Per Worker:",
    ]
    for w in summary["worker_breakdown"]:
        lines.append(f"  {w['worker']}: {w['total_pieces']} pcs, Net Rs {w['net']:,.2f}")
    return "\n".join(lines)


@function_tool
def get_worker_payslip_tool(worker: str, year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Generate pay slip for a specific worker in both PDF and Excel.

    Args:
        worker: Worker name (e.g., 'Ahmed')
        year: Year (default: current)
        month: Month 1-12 (default: current)

    Returns:
        Pay slip summary with file paths
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    data = calc_worker_payslip(worker, y, m)
    if "error" in data:
        return data["error"]
    pdf = generate_pdf_payslip(worker, y, m)
    xls = generate_excel_payslip(worker, y, m)
    lines = [f"Pay Slip for {worker} - {y}-{m:02d}", f"Net Payable: Rs {data['total_net']:,.2f}", ""]
    for pb in data["product_breakdown"]:
        lines.append(f"  {pb['product_code']}: {pb['quantity']} pcs = Rs {pb['gross']:,.2f}")
    lines.extend(["", f"PDF: {pdf}", f"Excel: {xls}"])
    return "\n".join(lines)


@function_tool
def send_daily_email_tool(year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Send daily production summary email to the manager.

    Args:
        year: Year (default: current)
        month: Month 1-12 (default: current)
        day: Day 1-31 (default: today)

    Returns:
        Email delivery status
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day
    summary = calc_daily_summary(y, m, d)
    return send_daily_summary(y, m, d, summary)


@function_tool
def list_workers_tool(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """List all workers who have entries in a given month.

    Args:
        year: Year (default: current)
        month: Month 1-12 (default: current)

    Returns:
        List of worker names
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    workers = get_all_workers(y, m)
    if not workers:
        return f"No workers found for {y}-{m:02d}"
    return f"Workers ({len(workers)}):\n" + "\n".join(f"  {i+1}. {w}" for i, w in enumerate(workers))


@function_tool
def get_worker_history_tool(worker: str, year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Get all work entries for a specific worker.

    Args:
        worker: Worker name (e.g., 'Ahmed')
        year: Year (default: current)
        month: Month 1-12 (default: current)

    Returns:
        List of all entries with dates and amounts
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    entries = get_worker_entries(worker, y, m)
    if not entries:
        return f"No entries for {worker} in {y}-{m:02d}"
    lines = [f"History for {worker} - {y}-{m:02d} ({len(entries)} entries):"]
    total = 0
    for e in entries:
        lines.append(f"  {e['date']} | {e['product_code']} | {e['quantity']} pcs | Net Rs {e['net']:,.2f}")
        total += e["net"]
    lines.append(f"\nTotal Net: Rs {total:,.2f}")
    return "\n".join(lines)


@function_tool
def list_products_tool() -> str:
    """List all products in the catalog with their rates.

    Returns:
        Product catalog
    """
    products = load_product_catalog()
    if not products:
        return "No products in catalog"
    lines = ["Product Catalog:"]
    for p in products:
        lines.append(f"  {p['product_code']}: {p['description']} - Rs {p['rate_per_piece']:,.2f}/pc")
    return "\n".join(lines)


@function_tool
def generate_all_payslips_tool(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Generate pay slips for ALL workers in a given month.

    Args:
        year: Year (default: current)
        month: Month 1-12 (default: current)

    Returns:
        List of generated files
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    workers = get_all_workers(y, m)
    if not workers:
        return f"No workers for {y}-{m:02d}"
    results = []
    for w in workers:
        pdf = generate_pdf_payslip(w, y, m)
        xls = generate_excel_payslip(w, y, m)
        results.append(f"  {w}: PDF, Excel")
    return f"Pay slips for {len(workers)} workers:\n" + "\n".join(results)


@function_tool
def get_current_date_tool() -> str:
    """Get the current date information.

    Returns:
        Current date
    """
    today = date.today()
    return f"Today: {today.isoformat()}"


@function_tool
def get_today_work_status_tool() -> str:
    """Check if any work has been recorded for TODAY. ALWAYS call this tool at the very start of EVERY conversation before anything else.

    Returns:
        Status message whether data exists for today or not
    """
    today = date.today()
    has_data = has_today_entries(today.year, today.month, today.day)
    if has_data:
        entries = [e for e in read_month_entries(today.year, today.month)
                   if e["date"] == today.isoformat()]
        workers = sorted(set(e["worker"] for e in entries))
        return (
            f"DATA_FOUND: {len(entries)} entries recorded for {today.isoformat()}. "
            f"Workers: {', '.join(workers)}"
        )
    return (
        f"NO_DATA: No work has been recorded for {today.isoformat()} yet. "
        f"Fixed workers: {', '.join(FIXED_WORKERS)}. "
        "You MUST remind the user to enter today's production data persistently."
    )


orchestrator_agent = Agent(
    name="AccountantOrchestrator",
    instructions="""You are an intelligent accounting assistant for a factory with these fixed workers:
Naeem, Kaleem, Akbar, Suny, Sajjad, Irfan, Kashif, Gulmast.

CRITICAL RULES — FOLLOW THEM IN ORDER:
1. At the START of EVERY conversation, ALWAYS call get_today_work_status_tool FIRST.
2. If it returns NO_DATA: you MUST remind the user to enter today's production. Keep reminding until they enter data.
3. You already know the current date from the status tool. Do NOT ask for dates.
4. Products: NUT (NUT-STD, NUT-M10), 10*20 (BOLT-10x20), 6*25 (BOLT-6x25), 6*30 (BOLT-6x30), 10*25 (BOLT-10x25)

Capabilities:
1. Record work - Record piece-rate work for workers
2. Record from text - Parse natural language descriptions (e.g., "Kaleem ne 300 nut buff kiye")
3. Daily reports - Get daily production totals
4. Monthly reports - Monthly summaries per worker
5. Worker history - View individual records
6. Pay slips - PDF + Excel pay slips
7. Email reports - Send daily summaries to manager
8. Product catalog - View products and rates
9. List workers - See fixed workers list

When user describes work in natural language, use record_work_from_text_tool.
For structured data use record_work_tool.
At month end, offer to generate pay slips for all workers.
Be helpful and respond in Urdu/English mix.
""",
    model=GEMINI_MODEL,
    tools=[
        record_work_tool, record_work_from_text_tool,
        get_daily_total_tool, get_monthly_summary_tool,
        get_worker_payslip_tool, send_daily_email_tool,
        list_workers_tool, get_worker_history_tool,
        list_products_tool, generate_all_payslips_tool,
        get_current_date_tool, get_today_work_status_tool,
    ],
)


async def chat(user_input: str) -> str:
    result = await Runner.run(orchestrator_agent, input=user_input)
    return result.final_output
