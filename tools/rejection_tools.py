import json
from typing import Optional

from tools.database import (
    log_rejection as db_log_rejection,
    get_rejections_for_month,
    get_active_workers,
)
from tools.production_tools import get_product_info


def log_rejection(
    year: int, month: int, product_code: str,
    total_qty: int, excluded_workers: Optional[list[str]] = None,
) -> str:
    product = get_product_info(product_code)
    if not product:
        return f"Unknown product '{product_code}'. Valid: NUT, 10*20, 6*25, 6*30, 10*25"

    if excluded_workers is None:
        excluded_workers = []

    rid = db_log_rejection(year, month, product["id"], total_qty, excluded_workers)

    active = get_active_workers()
    eligible = [w["name"] for w in active if w["name"] not in excluded_workers]

    if not eligible:
        return f"Rejection recorded (id={rid}). No eligible workers for distribution."

    base = total_qty // len(eligible)
    remainder = total_qty % len(eligible)

    lines = [
        f"Rejection recorded (id={rid}): {total_qty}x{product_code} for {year}-{month:02d}",
        f"Eligible workers ({len(eligible)}): {', '.join(eligible)}",
        f"Distribution: {base} each",
    ]
    if remainder:
        extra = eligible[:remainder]
        lines.append(f"Extra 1 piece to: {', '.join(extra)}")
    if excluded_workers:
        lines.append(f"Excluded: {', '.join(excluded_workers)}")

    return "\n".join(lines)


def get_distribution_for_month(year: int, month: int) -> list[dict]:
    rejections = get_rejections_for_month(year, month)
    active = get_active_workers()
    active_names = [w["name"] for w in active]

    result = []
    for r in rejections:
        exclude = r.get("exclude_workers", [])
        eligible = [n for n in active_names if n not in exclude]
        qty = r["total_qty"]
        if eligible:
            base = qty // len(eligible)
            remainder = qty % len(eligible)
            dist = {}
            for i, name in enumerate(eligible):
                dist[name] = base + (1 if i < remainder else 0)
        else:
            dist = {}
        result.append({
            "product_code": r["product_code"],
            "total_qty": qty,
            "distribution": dist,
        })
    return result
