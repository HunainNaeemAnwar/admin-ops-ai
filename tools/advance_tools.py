from typing import Optional

from tools.database import (
    record_advance as db_record_advance,
    get_advances_for_worker_month,
    get_total_advances_for_worker_month,
    get_worker_id, get_or_create_worker,
)


def record_advance(worker: str, amount: float, year: int, month: int, description: str = "") -> str:
    worker_id = get_or_create_worker(worker)
    aid = db_record_advance(worker_id, amount, year, month, description)
    total = get_total_advances_for_worker_month(worker_id, year, month)
    return (
        f"Advance recorded (id={aid}): Rs {amount:,.2f} for {worker} ({year}-{month:02d})\n"
        f"Total advances for {worker} this month: Rs {total:,.2f}"
    )


def get_advances_summary(year: int, month: int) -> str:
    from tools.database import get_all_workers
    workers = get_all_workers()
    lines = [f"Advances Summary - {year}-{month:02d}:"]
    total_all = 0.0
    for w in workers:
        wid = w["id"]
        advances = get_advances_for_worker_month(wid, year, month)
        if advances:
            total = sum(a["amount"] for a in advances)
            lines.append(f"  {w['name']}: Rs {total:,.2f} ({len(advances)} entries)")
            total_all += total
    if len(lines) == 1:
        return "No advances recorded for this month"
    lines.append(f"Total: Rs {total_all:,.2f}")
    return "\n".join(lines)
