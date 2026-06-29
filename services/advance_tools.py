from typing import Optional

from services.database import (
    record_advance as db_record_advance,
    get_advances_for_worker_month,
    get_total_advances_for_worker_month,
    get_all_advances_for_month,
    get_worker_id, get_or_create_worker,
)


def record_worker_advance(worker: str, amount: float, year: int, month: int, description: str = "") -> str:
    if amount <= 0:
        return f"⚠️ Amount must be positive, got Rs {amount:,.2f}"
    worker_id = get_or_create_worker(worker)
    existing = get_advances_for_worker_month(worker_id, year, month)
    for adv in existing:
        if adv["amount"] == amount and adv["description"] == description:
            return (
                f"⚠️ Duplicate advance: Rs {amount:,.2f} already recorded for {worker} "
                f"({year}-{month:02d}, id={adv['id']}). Skip kiya."
            )
    existing_total = sum(a["amount"] for a in existing)
    aid = db_record_advance(worker_id, amount, year, month, description)
    total = existing_total + amount
    return (
        f"Advance recorded (id={aid}): Rs {amount:,.2f} for {worker} ({year}-{month:02d})\n"
        f"Total advances for {worker} this month: Rs {total:,.2f}"
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
    rows = get_all_advances_for_month(year, month)
    if not rows:
        return "No advances recorded for this month"
    worker_advances: dict[str, list[float]] = {}
    for r in rows:
        name = r["worker_name"]
        if name not in worker_advances:
            worker_advances[name] = []
        worker_advances[name].append(r["amount"])
    lines = [f"Advances Summary - {year}-{month:02d}:"]
    total_all = 0.0
    for name in sorted(worker_advances):
        amounts = worker_advances[name]
        total = sum(amounts)
        lines.append(f"  {name}: Rs {total:,.2f} ({len(amounts)} entries)")
        total_all += total
    lines.append(f"Total: Rs {total_all:,.2f}")
    return "\n".join(lines)
