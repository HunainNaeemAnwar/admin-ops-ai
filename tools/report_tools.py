from datetime import date, timedelta
from typing import Optional

from config import FIXED_WORKERS
from tools.database import (
    get_logs_for_date, get_daily_totals,
    get_active_workers, get_all_products,
)


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

    present = set()
    totals = {}
    for log in logs:
        if log["status"] == "present":
            present.add(log["worker_name"])
            prod = log["product_code"]
            totals[prod] = totals.get(prod, 0) + log["quantity"]

    absent = [w for w in FIXED_WORKERS if w not in present]
    lines = [
        f"DATA_FOUND: {len(logs)} entries for {date_str}",
        f"Workers present ({len(present)}): {', '.join(sorted(present))}",
    ]
    if totals:
        lines.append("Product totals:")
        for code, qty in sorted(totals.items()):
            lines.append(f"  {code}: {qty} pcs")
    if absent:
        lines.append(f"Absent: {', '.join(absent)}")
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
    totals = get_daily_totals(date_str)
    logs = get_logs_for_date(date_str)
    present = set(l["worker_name"] for l in logs if l["status"] == "present")
    total_pieces = sum(totals.values())

    lines = [
        f"Daily Summary - {date_str}",
        f"Workers present: {len(present)} | Total pieces: {total_pieces}",
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
    week_totals = {}
    for i in range(7):
        d = monday + timedelta(days=i)
        ds = d.isoformat()
        totals = get_daily_totals(ds)
        day_total = sum(totals.values())
        if day_total > 0:
            week_totals[ds] = totals
            lines.append(f"  {d.strftime('%A')} ({ds}): {day_total} pcs")
            for code, qty in sorted(totals.items()):
                lines.append(f"    {code}: {qty}")

    if not week_totals:
        lines.append("  No production recorded for this week.")
    return "\n".join(lines)


def _monthly_summary(year: int, month: int) -> str:
    lines = [f"Monthly Summary - {year}-{month:02d}"]
    workers = get_active_workers()
    products = get_all_products()
    product_codes = [p["code"] for p in products]

    grand_totals = {code: 0 for code in product_codes}
    total_pieces = 0

    for w in workers:
        wid = w["id"]
        from tools.database import get_worker_month_production
        entries = get_worker_month_production(wid, year, month)
        if entries:
            worker_totals = {}
            for e in entries:
                code = e["product_code"]
                worker_totals[code] = worker_totals.get(code, 0) + e["quantity"]
            worker_total = sum(worker_totals.values())
            total_pieces += worker_total
            parts = [f"{code}: {qty}" for code, qty in sorted(worker_totals.items())]
            lines.append(f"  {w['name']}: {worker_total} pcs ({', '.join(parts)})")
            for code, qty in worker_totals.items():
                grand_totals[code] += qty

    lines.append(f"\nGrand Total: {total_pieces} pieces")
    for code in product_codes:
        if grand_totals[code] > 0:
            lines.append(f"  {code}: {grand_totals[code]} pcs")
    return "\n".join(lines)
