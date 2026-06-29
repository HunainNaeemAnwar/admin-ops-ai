from datetime import date, timedelta
from typing import Optional

from config import FIXED_WORKERS
from services.database import (
    get_logs_for_date, get_date_range_totals,
    get_active_workers, get_all_products,
)
from services.production_tools import get_product_info


def get_daily_status(date_str: Optional[str] = None) -> str:
    if date_str is None:
        date_str = date.today().isoformat()

    logs = get_logs_for_date(date_str)
    if not logs:
        return (
            f"NO_DATA: No work recorded for {date_str}.\n"
            f"Fixed workers: {', '.join(FIXED_WORKERS)}\n"
            "Please enter today's production data."
        )

    present: dict[str, dict[str, int]] = {}
    product_totals: dict[str, int] = {}
    entry_lines = []
    for log in logs:
        if log["status"] == "present":
            wname = log["worker_name"]
            code = log["product_code"]
            qty = log["quantity"]
            if wname not in present:
                present[wname] = {}
            present[wname][code] = present[wname].get(code, 0) + qty
            product_totals[code] = product_totals.get(code, 0) + qty
            entry_lines.append(
                f"  ID#{log['id']} | {wname} | {code} | {qty}"
            )

    absent_reasons: dict[str, str] = {}
    for log in logs:
        if log["status"] == "absent" and log["reason"]:
            absent_reasons[log["worker_name"]] = log["reason"]

    absent = [w for w in FIXED_WORKERS if w not in present]
    lines = [
        f"DATA_FOUND: {date_str} — {len(present)} workers present",
        "",
        "Worker-wise production:",
    ]
    for wname in sorted(present):
        items = sorted(present[wname].items())
        parts = [f"{code}={qty:,}" for code, qty in items]
        lines.append(f"  {wname}: {', '.join(parts)}")

    lines.append("")
    lines.append("Product-wise totals:")
    for code, qty in sorted(product_totals.items()):
        lines.append(f"  {code}: {qty:,} pcs")

    if entry_lines:
        lines.append("")
        lines.append("Entry IDs (use for update):")
        lines.extend(entry_lines)

    lines.append("")
    if absent:
        abs_parts = []
        for w in absent:
            r = absent_reasons.get(w)
            abs_parts.append(f"{w} ({r})" if r else w)
        lines.append(f"Absent: {', '.join(abs_parts)}")
    else:
        lines.append("Absent: (none)")
    return "\n".join(lines)


def get_summary(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    today = date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day

    if period == "daily":
        return _daily_summary(y, m, d)
    elif period == "weekly":
        return _weekly_summary(y, m, d)
    elif period == "monthly":
        return _monthly_summary(y, m)
    else:
        return f"Unknown period '{period}'. Use: daily, weekly, monthly"


def _daily_summary(year: int, month: int, day: int) -> str:
    date_str = f"{year}-{month:02d}-{day:02d}"
    logs = get_logs_for_date(date_str)
    present = set()
    totals: dict[str, int] = {}
    for log in logs:
        if log["status"] == "present":
            present.add(log["worker_name"])
            code = log["product_code"]
            totals[code] = totals.get(code, 0) + log["quantity"]

    lines = [
        f"Daily Summary - {date_str}",
        f"Workers present: {len(present)}",
    ]
    for code, qty in sorted(totals.items()):
        lines.append(f"  {code}: {qty} pcs")
    absent = [w for w in FIXED_WORKERS if w not in present]
    if absent:
        lines.append(f"Absent: {', '.join(absent)}")
    return "\n".join(lines)


def _weekly_summary(year: int, month: int, day: int) -> str:
    dt = date(year, month, day)
    monday = dt - timedelta(days=dt.weekday())
    sunday = monday + timedelta(days=6)
    lines = [f"Weekly Summary - {monday.isoformat()} to {sunday.isoformat()}"]
    rows = get_date_range_totals(monday.isoformat(), sunday.isoformat())
    week_totals: dict[str, dict[str, int]] = {}
    for r in rows:
        ds = r["entry_date"]
        if ds not in week_totals:
            week_totals[ds] = {}
        week_totals[ds][r["product_code"]] = r["total_qty"]

    for i in range(7):
        d = monday + timedelta(days=i)
        ds = d.isoformat()
        totals = week_totals.get(ds)
        if totals:
            lines.append(f"  {d.strftime('%A')} ({ds}):")
            for code, qty in sorted(totals.items()):
                lines.append(f"    {code}: {qty}")

    if not week_totals:
        lines.append("  No production recorded for this week.")
    return "\n".join(lines)


def _monthly_summary(year: int, month: int) -> str:
    workers = get_active_workers()
    products = get_all_products()
    product_codes = [p["code"] for p in products]

    header = "| Worker | " + " | ".join(product_codes) + " |"
    sep = "|--------|" + "|".join("-------" for _ in product_codes) + "|"

    from services.database import get_all_workers_month_production
    prod_rows = get_all_workers_month_production(year, month)
    worker_data: dict[int, dict[str, int]] = {}
    worker_names: dict[int, str] = {}
    for r in prod_rows:
        wid = r["worker_id"]
        worker_names[wid] = r["worker_name"]
        if wid not in worker_data:
            worker_data[wid] = {}
        worker_data[wid][r["product_code"]] = r["total_qty"]

    table_rows = []
    for w in workers:
        wid = w["id"]
        if wid in worker_data:
            totals = worker_data[wid]
            values = [f"{totals.get(c, 0):,}" for c in product_codes]
            table_rows.append(f"| {w['name']} | " + " | ".join(values) + " |")

    all_rows = [f"**Monthly Summary - {year}-{month:02d}**", "", header, sep] + table_rows

    if not table_rows:
        all_rows.append("_No production data for this month._")

    return "\n".join(all_rows)


def get_production_summary(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    today = date.today()
    y = year or today.year
    m = month or (today.month if y == today.year else 1)
    d = day or (today.day if y == today.year and m == today.month else 1)
    return get_summary(period, y, m, d)


def get_catalog() -> str:
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
    lines.append(f"\nToday's Status:")
    lines.append(f"  {get_daily_status()}")
    return "\n".join(lines)
