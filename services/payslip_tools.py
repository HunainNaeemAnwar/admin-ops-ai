from config import TAX_PERCENTAGE
from services.database import (
    get_worker_id, get_worker_month_production, get_worker_rejection_share,
    get_payslip, get_total_advances_for_worker_month, get_all_products,
)
from services.rejection_tools import get_distribution_for_month
from services.payslip_template import render_pdf_payslip


def _build_payslip_data(worker: str, year: int, month: int) -> dict | None:
    wid = get_worker_id(worker)
    if not wid:
        return None

    ps = get_payslip(wid, year, month)

    production = get_worker_month_production(wid, year, month)
    products = get_all_products()
    product_rates = {p["code"]: p["rate"] for p in products}

    product_totals = {}
    if production:
        for p in production:
            code = p["product_code"]
            product_totals[code] = product_totals.get(code, 0) + p["quantity"]

    worker_rejection_share = get_worker_rejection_share(worker, year, month)

    if ps:
        result = dict(ps)
        result["product_totals"] = product_totals
        result["product_rates"] = product_rates
        result["worker_rejection_share"] = worker_rejection_share
        return result

    if not production:
        return None

    gross_total = sum(qty * product_rates.get(code, 0) for code, qty in product_totals.items())

    distribution = get_distribution_for_month(year, month)

    rejection_deduction = 0
    for dist in distribution:
        w_share = dist["distribution"].get(worker, 0)
        rejection_deduction += w_share * product_rates.get(dist["product_code"], 0)

    advance_deduction = get_total_advances_for_worker_month(wid, year, month)

    tax_amount = round(gross_total * TAX_PERCENTAGE / 100, 2)
    net_payable = round(gross_total - rejection_deduction - advance_deduction - tax_amount, 2)

    return {
        "gross_total": gross_total,
        "tax_total": tax_amount,
        "rejection_deduction": rejection_deduction,
        "advance_deduction": advance_deduction,
        "net_payable": net_payable,
        "product_totals": product_totals,
        "product_rates": product_rates,
        "worker_rejection_share": worker_rejection_share,
    }


def generate_pdf_payslip(worker: str, year: int, month: int) -> str:
    data = _build_payslip_data(worker, year, month)
    if not data:
        return f"No data for {worker} in {year}-{month:02d}"
    return render_pdf_payslip(data, worker, year, month)


