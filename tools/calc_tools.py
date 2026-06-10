from tools.excel_tools import (
    lookup_product, load_product_catalog, read_month_entries,
    get_daily_total, get_monthly_total, get_worker_monthly_total,
    get_worker_entries, get_all_workers
)
from config import TAX_PERCENTAGE


def calc_piece_rate(product_code: str, quantity: int) -> dict:
    product = lookup_product(product_code)
    if not product:
        return {"error": f"Product '{product_code}' not found in catalog"}
    rate = product["rate_per_piece"]
    tax_pct = product["tax_pct"] if product["tax_pct"] > 0 else TAX_PERCENTAGE
    gross = round(quantity * rate, 2)
    tax_amt = round(gross * tax_pct / 100, 2)
    net = round(gross - tax_amt, 2)
    return {
        "product_code": product["product_code"],
        "description": product["description"],
        "rate": rate,
        "quantity": quantity,
        "gross": gross,
        "tax_pct": tax_pct,
        "tax_amt": tax_amt,
        "net": net,
    }


def calc_daily_summary(year: int, month: int, day: int) -> dict:
    total = get_daily_total(year, month, day)
    entries = [e for e in read_month_entries(year, month)
               if e["date"] == f"{year}-{month:02d}-{day:02d}"]
    workers = set(e["worker"] for e in entries)
    total_pieces = sum(e["quantity"] for e in entries)
    total_gross = sum(e["gross"] for e in entries)
    total_tax = sum(e["tax_amt"] for e in entries)
    return {
        "date": f"{year}-{month:02d}-{day:02d}",
        "workers_count": len(workers),
        "workers": sorted(workers),
        "entries_count": len(entries),
        "total_pieces": total_pieces,
        "total_gross": round(total_gross, 2),
        "total_tax": round(total_tax, 2),
        "total_net": round(total, 2),
    }


def calc_monthly_summary(year: int, month: int) -> dict:
    entries = read_month_entries(year, month)
    workers = set(e["worker"] for e in entries if e["worker"])
    total_pieces = sum(e["quantity"] for e in entries)
    total_gross = sum(e["gross"] for e in entries)
    total_tax = sum(e["tax_amt"] for e in entries)
    total_net = sum(e["net"] for e in entries)
    worker_breakdown = []
    for w in sorted(workers):
        we = [e for e in entries if e["worker"] == w]
        worker_breakdown.append({
            "worker": w,
            "entries": len(we),
            "total_pieces": sum(e["quantity"] for e in we),
            "gross": round(sum(e["gross"] for e in we), 2),
            "tax": round(sum(e["tax_amt"] for e in we), 2),
            "net": round(sum(e["net"] for e in we), 2),
        })
    return {
        "year": year,
        "month": month,
        "total_workers": len(workers),
        "total_entries": len(entries),
        "total_pieces": total_pieces,
        "total_gross": round(total_gross, 2),
        "total_tax": round(total_tax, 2),
        "total_net": round(total_net, 2),
        "worker_breakdown": worker_breakdown,
    }


def calc_worker_payslip(worker: str, year: int, month: int) -> dict:
    entries = get_worker_entries(worker, year, month)
    if not entries:
        return {"error": f"No entries found for {worker} in {year}-{month:02d}"}
    total_pieces = sum(e["quantity"] for e in entries)
    total_gross = sum(e["gross"] for e in entries)
    total_tax = sum(e["tax_amt"] for e in entries)
    total_net = sum(e["net"] for e in entries)
    product_breakdown = {}
    for e in entries:
        pc = e["product_code"]
        if pc not in product_breakdown:
            product_breakdown[pc] = {"product_code": pc, "description": e["description"], "quantity": 0, "gross": 0}
        product_breakdown[pc]["quantity"] += e["quantity"]
        product_breakdown[pc]["gross"] += e["gross"]
    return {
        "worker": worker,
        "year": year,
        "month": month,
        "total_entries": len(entries),
        "total_pieces": total_pieces,
        "total_gross": round(total_gross, 2),
        "total_tax": round(total_tax, 2),
        "total_net": round(total_net, 2),
        "product_breakdown": list(product_breakdown.values()),
    }
