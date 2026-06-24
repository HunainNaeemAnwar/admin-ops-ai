from typing import Optional

from fastmcp import FastMCP

from config import TAX_PERCENTAGE, MANAGER_EMAIL
from tools.database import (
    get_all_workers, get_all_products, get_daily_totals,
    get_logs_for_date, get_worker_month_production,
)
from tools.production_tools import log_production_json, calc_piece_rate
from tools.rejection_tools import log_rejection
from tools.advance_tools import record_advance
from tools.report_tools import get_daily_status, get_summary
from tools.email_tools import send_report
from tools.payslip_tools import generate_pdf_payslip

mcp = FastMCP("accountant_mcp")


@mcp.tool()
def log_production_entry(entries_json: str) -> str:
    """Record daily production. Pass JSON array string.
    Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]
    """
    return log_production_json(entries_json)


@mcp.tool()
def log_rejection_entry(product_code: str, total_qty: int, year: int, month: int, excluded_workers: Optional[str] = None) -> str:
    """Record department-level rejection that is equally distributed among all active workers.
    Args:
        product_code: Product code (NUT, 10*20, 6*25, 6*30, 10*25)
        total_qty: Total rejected pieces
        year: Year
        month: Month 1-12
        excluded_workers: JSON array of worker names to exclude from distribution
    """
    import json
    excluded = json.loads(excluded_workers) if excluded_workers else []
    return log_rejection(year, month, product_code, total_qty, excluded)


@mcp.tool()
def record_advance_entry(worker: str, amount: float, year: int, month: int, description: str = "") -> str:
    """Record an advance payment to a worker."""
    return record_advance(worker, amount, year, month, description)


@mcp.tool()
def mark_absent_entry(workers: str, date_str: Optional[str] = None) -> str:
    """Mark workers as absent for a date. Use 'all' to mark all workers."""
    from tools.production_tools import mark_absent, mark_all_absent
    from datetime import date
    if date_str is None:
        date_str = date.today().isoformat()
    if workers.lower() == "all":
        return mark_all_absent(date_str)
    return mark_absent(workers, date_str)


@mcp.tool()
def get_daily_status_query(date_str: Optional[str] = None) -> str:
    """Check if production data exists for a date."""
    return get_daily_status(date_str)


@mcp.tool()
def get_production_summary(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Get production summary. Period: daily, weekly, or monthly."""
    return get_summary(period, year, month, day)


@mcp.tool()
def generate_worker_payslip(worker: str, year: int, month: int) -> str:
    """Generate PDF payslip for a worker."""
    pdf = generate_pdf_payslip(worker, year, month)
    return f"PDF: {pdf}"


@mcp.tool()
def send_production_report(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Send production report to manager. Quantities only - no financial data."""
    from datetime import date
    today = date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day
    return send_report(period, y, m, d)


@mcp.tool()
def update_production_entry(entry_id: int, new_quantity: int, reason: str = "") -> str:
    """Update a production entry quantity."""
    from tools.production_tools import update_entry
    return update_entry(entry_id, new_quantity, reason)


@mcp.tool()
def list_system_catalog() -> str:
    """List all active workers and products with rates."""
    from datetime import date
    workers = get_all_workers()
    products = get_all_products()
    lines = [
        f"Today: {date.today().isoformat()}",
        f"Workers ({len(workers)}):",
    ]
    for w in workers:
        lines.append(f"  {w['name']}")
    lines.append(f"\nProducts:")
    for p in products:
        lines.append(f"  {p['code']}: Rs {p['rate']:,.2f}/pc")
    return "\n".join(lines)


mcp_app = mcp.http_app(path="/")


if __name__ == "__main__":
    mcp.run()
