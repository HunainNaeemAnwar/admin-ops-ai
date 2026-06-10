import asyncio
from datetime import date, datetime
from typing import Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from config import TAX_PERCENTAGE, MANAGER_EMAIL
from tools.excel_tools import (
    append_work_entry, lookup_product, load_product_catalog,
    read_month_entries, get_all_workers, get_worker_entries,
)
from tools.calc_tools import (
    calc_piece_rate, calc_daily_summary, calc_monthly_summary,
    calc_worker_payslip,
)
from tools.email_tools import send_email, send_daily_summary
from tools.payslip_tools import generate_pdf_payslip, generate_excel_payslip
from agent_system.data_extractor import extract_from_text

mcp = FastMCP("accountant_mcp")

class RecordWorkInput(BaseModel):
    worker: str = Field(description="Worker name (e.g., 'Ahmed')")
    product_code: str = Field(description="Product code (e.g., 'BOLT-10x20', 'NUT-STD')")
    quantity: int = Field(description="Number of pieces completed", ge=1)

@mcp.tool(
    annotations={
        "title": "Record Work Entry",
        "destructiveHint": False,
        "idempotentHint": False,
        "readOnlyHint": False,
        "openWorldHint": False,
    }
)
async def record_work(worker: str, product_code: str, quantity: int) -> str:
    """Record a daily work entry for a worker.
    
    Use this when a worker has completed pieces of a specific product.
    Automatically looks up the rate, calculates gross/tax/net, and saves to Excel.
    
    Args:
        worker: Worker's name (e.g., "Ahmed", "Ali", "Sarfaraz")
        product_code: Product code from catalog (e.g., "BOLT-10x20", "NUT-STD", "BOLT-6x25")
        quantity: Number of pieces completed (positive integer)
    
    Returns:
        Confirmation message with calculated amounts
    """
    result = calc_piece_rate(product_code, quantity)
    if "error" in result:
        catalog = load_product_catalog()
        available = ", ".join(p["product_code"] for p in catalog)
        return f"{result['error']}. Available products: {available}"
    
    append_work_entry(
        worker=worker,
        product_code=result["product_code"],
        description=result["description"],
        quantity=result["quantity"],
        rate=result["rate"],
        gross=result["gross"],
        tax_pct=result["tax_pct"],
        tax_amt=result["tax_amt"],
        net=result["net"],
    )
    return (
        f"Recorded: {worker} - {result['quantity']}×{result['product_code']} "
        f"({result['description']})\n"
        f"Gross: Rs {result['gross']:,.2f} | "
        f"Tax ({result['tax_pct']:.0f}%): Rs {result['tax_amt']:,.2f} | "
        f"Net: Rs {result['net']:,.2f}"
    )

@mcp.tool(
    annotations={
        "title": "Record Work from Text",
        "readOnlyHint": False,
        "destructiveHint": False,
    }
)
async def record_work_from_text(text: str) -> str:
    """Record work entries from natural language text.
    
    Use this when someone describes work in plain language instead of structured data.
    Example: 'Ahmed ne 50 bolt 10*20 aur 30 nuts buff kiye'
    
    Args:
        text: Natural language description of work done
    
    Returns:
        Summary of all recorded entries
    """
    parsed = await extract_from_text(text)
    results = []
    for prod in parsed.products:
        result = calc_piece_rate(prod.product_code, prod.quantity)
        if "error" in result:
            results.append(f"  {prod.product_code}: {result['error']}")
            continue
        append_work_entry(
            worker=parsed.worker,
            product_code=result["product_code"],
            description=result["description"],
            quantity=result["quantity"],
            rate=result["rate"],
            gross=result["gross"],
            tax_pct=result["tax_pct"],
            tax_amt=result["tax_amt"],
            net=result["net"],
        )
        results.append(
            f"  {result['quantity']}×{result['product_code']} → "
            f"Gross Rs {result['gross']:,.2f}, Net Rs {result['net']:,.2f}"
        )
    total_net = sum(
        calc_piece_rate(p.product_code, p.quantity)["net"]
        for p in parsed.products
        if "error" not in calc_piece_rate(p.product_code, p.quantity)
    )
    return f"Recorded {len(results)} entries for {parsed.worker}:\n" + "\n".join(results) + f"\nTotal Net: Rs {total_net:,.2f}"

@mcp.tool(
    annotations={
        "title": "Get Daily Total",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def get_daily_total(year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Get the total production amount for a specific day.
    
    Args:
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
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
        f"Gross: Rs {summary['total_gross']:,.2f}\n"
        f"Tax: Rs {summary['total_tax']:,.2f}\n"
        f"Net Total: Rs {summary['total_net']:,.2f}\n"
        f"Workers: {', '.join(summary['workers']) if summary['workers'] else 'None'}"
    )

@mcp.tool(
    annotations={
        "title": "Get Monthly Summary",
        "readOnlyHint": True,
        "idempotentHint": True,
    }
)
async def get_monthly_summary(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Get complete monthly production summary with per-worker breakdown.
    
    Args:
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
    
    Returns:
        Monthly report with totals and worker breakdown
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    summary = calc_monthly_summary(y, m)
    lines = [
        f"Monthly Summary - {y}-{m:02d}",
        f"Total Workers: {summary['total_workers']}",
        f"Total Entries: {summary['total_entries']}",
        f"Total Pieces: {summary['total_pieces']}",
        f"Total Gross: Rs {summary['total_gross']:,.2f}",
        f"Total Tax: Rs {summary['total_tax']:,.2f}",
        f"Total Net: Rs {summary['total_net']:,.2f}",
        "",
        "Worker Breakdown:",
    ]
    for w in summary["worker_breakdown"]:
        lines.append(f"  {w['worker']}: {w['total_pieces']} pcs, Gross Rs {w['gross']:,.2f}, Net Rs {w['net']:,.2f}")
    return "\n".join(lines)

@mcp.tool(
    annotations={
        "title": "Get Worker Pay Slip",
        "readOnlyHint": True,
        "idempotentHint": True,
    }
)
async def get_worker_payslip(worker: str, year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Generate pay slip for a specific worker in both PDF and Excel formats.
    
    Args:
        worker: Worker name (e.g., 'Ahmed')
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
    
    Returns:
        Paths to generated pay slip files
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    data = calc_worker_payslip(worker, y, m)
    if "error" in data:
        return data["error"]
    pdf_path = generate_pdf_payslip(worker, y, m)
    excel_path = generate_excel_payslip(worker, y, m)
    lines = [
        f"Pay Slip for {worker} - {y}-{m:02d}",
        f"Total Pieces: {data['total_pieces']}",
        f"Gross: Rs {data['total_gross']:,.2f}",
        f"Tax: Rs {data['total_tax']:,.2f}",
        f"Net Payable: Rs {data['total_net']:,.2f}",
        "",
        "Product Breakdown:",
    ]
    for pb in data["product_breakdown"]:
        lines.append(f"  {pb['product_code']}: {pb['quantity']} pcs × Rs = Rs {pb['gross']:,.2f}")
    lines.extend([
        "",
        f"PDF: {pdf_path}",
        f"Excel: {excel_path}",
    ])
    return "\n".join(lines)

@mcp.tool(
    annotations={
        "title": "Send Daily Email Report",
        "readOnlyHint": True,
        "destructiveHint": False,
    }
)
async def send_daily_email_report(year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Send daily production summary email to the manager.
    
    Args:
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
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

@mcp.tool(
    annotations={
        "title": "List Workers",
        "readOnlyHint": True,
        "idempotentHint": True,
    }
)
async def list_workers(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """List all workers who have entries in a given month.
    
    Args:
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
    
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

@mcp.tool(
    annotations={
        "title": "Get Worker History",
        "readOnlyHint": True,
        "idempotentHint": True,
    }
)
async def get_worker_history(worker: str, year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Get all work entries for a specific worker.
    
    Args:
        worker: Worker name (e.g., 'Ahmed')
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
    
    Returns:
        List of all entries for the worker
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    entries = get_worker_entries(worker, y, m)
    if not entries:
        return f"No entries found for {worker} in {y}-{m:02d}"
    lines = [f"Work History for {worker} - {y}-{m:02d} ({len(entries)} entries):", ""]
    total_net = 0
    for e in entries:
        lines.append(
            f"  {e['date']} | {e['product_code']} | {e['quantity']} pcs | "
            f"Gross Rs {e['gross']:,.2f} | Net Rs {e['net']:,.2f}"
        )
        total_net += e["net"]
    lines.append(f"\nTotal Net: Rs {total_net:,.2f}")
    return "\n".join(lines)

@mcp.tool(
    annotations={
        "title": "List Products",
        "readOnlyHint": True,
        "idempotentHint": True,
    }
)
async def list_products() -> str:
    """List all products in the catalog with their current rates.
    
    Returns:
        Product catalog with codes, descriptions, and rates
    """
    products = load_product_catalog()
    if not products:
        return "No products in catalog"
    lines = ["Product Catalog:", ""]
    for p in products:
        lines.append(f"  {p['product_code']}: {p['description']} - Rs {p['rate_per_piece']:,.2f}/pc ({p['tax_pct']:.0f}% tax)")
    return "\n".join(lines)

@mcp.tool(
    annotations={
        "title": "Get Current Date Info",
        "readOnlyHint": True,
        "idempotentHint": True,
    }
)
async def get_current_date_info() -> str:
    """Get the current date, month, and year information.
    
    Returns:
        Current date details
    """
    today = date.today()
    return f"Today: {today.isoformat()} (Year: {today.year}, Month: {today.month:02d}, Day: {today.day:02d})"

@mcp.tool(
    annotations={
        "title": "Generate All Pay Slips",
        "destructiveHint": False,
        "readOnlyHint": True,
    }
)
async def generate_all_payslips(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Generate pay slips for ALL workers for a given month.
    
    Args:
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
    
    Returns:
        List of all generated pay slip files
    """
    today = date.today()
    y = year or today.year
    m = month or today.month
    workers = get_all_workers(y, m)
    if not workers:
        return f"No workers found for {y}-{m:02d}"
    results = []
    for worker in workers:
        pdf = generate_pdf_payslip(worker, y, m)
        xls = generate_excel_payslip(worker, y, m)
        results.append(f"  {worker}: PDF={pdf}, Excel={xls}")
    return f"Generated pay slips for {len(workers)} workers:\n" + "\n".join(results)

if __name__ == "__main__":
    mcp.run()
