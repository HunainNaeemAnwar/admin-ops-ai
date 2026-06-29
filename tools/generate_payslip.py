from datetime import date
from typing import Optional

from agents import function_tool
from config import TAX_PERCENTAGE
from services.database import (
    get_active_workers, get_worker_id,
    get_worker_month_production,
    get_total_advances_for_worker_month,
    get_payslip, save_payslip,
)
from services.production_tools import get_product_info
from services.rejection_tools import get_distribution_for_month
from services.payslip_tools import generate_pdf_payslip


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

        existing = get_payslip(wid, y, m)

        save_payslip(wid, y, m, gross_total, tax_amount, rejection_value, advance_total, net_payable)
        generate_pdf_payslip(w, y, m)

        label = "Regenerated" if existing else "Generated"
        results.append(
            f"  {w}: {y}-{m:02d} payslip {label} — "
            f"Gross Rs {gross_total:,.0f}, "
            f"Net Rs {net_payable:,.0f}"
        )

    if not results:
        return "No payslips generated."
    return f"Payslips for {y}-{m:02d}:\n" + "\n".join(results)
