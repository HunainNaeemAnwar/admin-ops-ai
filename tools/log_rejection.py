import json
from typing import Optional

from agents import function_tool
from services.rejection_tools import record_rejection


@function_tool
def log_rejection_tool(year: int, month: int, product_code: str, total_qty: int, excluded_workers: Optional[str] = None) -> str:
    """Record department-level rejection for a month.

    Rejection is equally distributed among eligible workers.

    Args:
        year: Year (e.g. 2026)
        month: Month 1-12
        product_code: NUT, 10*20, 6*25, 6*30, or 10*25
        total_qty: Total rejected pieces
        excluded_workers: JSON array of workers to exclude, or null

    Returns:
        Distribution confirmation.
    """
    excluded = []
    if excluded_workers:
        try:
            excluded = json.loads(excluded_workers)
        except (json.JSONDecodeError, TypeError):
            excluded = [excluded_workers]
    return record_rejection(year, month, product_code, total_qty, excluded)
