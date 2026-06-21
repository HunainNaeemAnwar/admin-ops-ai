from tools.excel_tools import (
    lookup_product, load_product_catalog, read_month_entries,
    get_daily_total, get_monthly_total, get_worker_monthly_total,
    get_worker_entries, get_all_workers, _product_to_template_col, TEMPLATE_COLS,
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


def _filter_entries(entries: list, start_date: str, end_date: str) -> list:
    return [e for e in entries if start_date <= e["date"] <= end_date]


def _aggregate_products(entries: list) -> dict:
    products = {}
    for col in TEMPLATE_COLS[1:]:
        products[col] = 0
    for e in entries:
        col = _product_to_template_col(e["product_code"])
        if col and col in products:
            products[col] += abs(e["quantity"])
    return products


def calc_daily_products(year: int, month: int, day: int) -> dict:
    entries = read_month_entries(year, month)
    date_str = f"{year}-{month:02d}-{day:02d}"
    filtered = _filter_entries(entries, date_str, date_str)
    return _aggregate_products(filtered)


def calc_weekly_products(year: int, month: int, day: int) -> dict:
    from datetime import date, timedelta
    dt = date(year, month, day)
    monday = dt - timedelta(days=dt.weekday())
    sunday = monday + timedelta(days=6)
    start = monday.isoformat()
    end = sunday.isoformat()
    entries = []
    for m in range(1, 13):
        entries.extend(read_month_entries(year, m))
    filtered = _filter_entries(entries, start, end)
    return _aggregate_products(filtered)


def calc_monthly_products(year: int, month: int) -> dict:
    entries = read_month_entries(year, month)
    return _aggregate_products(entries)


def calc_weekly_daywise(year: int, month: int, day: int) -> list[dict]:
    from datetime import date, timedelta
    dt = date(year, month, day)
    monday = dt - timedelta(days=dt.weekday())
    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        days.append({
            "date": d.isoformat(),
            "day_name": d.strftime("%A"),
            "products": calc_daily_products(d.year, d.month, d.day),
        })
    return days


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


def _is_reject(entry: dict) -> bool:
    desc = (entry.get("description") or "").upper()
    return desc.startswith("REJECT:") or entry.get("quantity", 0) < 0


def calc_worker_payslip(worker: str, year: int, month: int) -> dict:
    entries = get_worker_entries(worker, year, month)
    if not entries:
        return {"error": f"No entries found for {worker} in {year}-{month:02d}"}

    template_breakdown = {}
    for col in TEMPLATE_COLS[1:]:
        template_breakdown[col] = {"good_qty": 0, "reject_qty": 0, "gross": 0.0, "tax": 0.0, "net": 0.0}

    for e in entries:
        col_name = _product_to_template_col(e["product_code"])
        if not col_name:
            continue
        td = template_breakdown[col_name]
        if _is_reject(e):
            td["reject_qty"] += abs(e["quantity"])
        else:
            td["good_qty"] += e["quantity"]
        td["gross"] += e["gross"]
        td["tax"] += e["tax_amt"]
        td["net"] += e["net"]

    net_total = sum(td["net"] for td in template_breakdown.values())
    gross_total = sum(td["gross"] for td in template_breakdown.values())
    tax_total = sum(td["tax"] for td in template_breakdown.values())
    total_pieces = sum(td["good_qty"] + td["reject_qty"] for td in template_breakdown.values())

    product_breakdown = []
    for col in TEMPLATE_COLS[1:]:
        td = template_breakdown[col]
        net_qty = td["good_qty"] - td["reject_qty"]
        product_breakdown.append({
            "item": col,
            "good_qty": td["good_qty"],
            "reject_qty": td["reject_qty"],
            "net_qty": net_qty,
            "gross": round(td["gross"], 2),
            "tax": round(td["tax"], 2),
            "net": round(td["net"], 2),
        })

    return {
        "worker": worker,
        "year": year,
        "month": month,
        "total_entries": len(entries),
        "total_pieces": total_pieces,
        "total_gross": round(gross_total, 2),
        "total_tax": round(tax_total, 2),
        "total_net": round(net_total, 2),
        "product_breakdown": product_breakdown,
    }
