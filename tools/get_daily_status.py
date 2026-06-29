import re
from datetime import date
from typing import Optional

from agents import function_tool
from services.report_tools import get_daily_status as get_date_status


@function_tool
def get_daily_status_tool(date_str: Optional[str] = None) -> str:
    """Check production data for a date. Shows present/absent workers and totals.

    Args:
        date_str: Date YYYY-MM-DD (default: today).

    Returns:
        Status with present/absent workers and product totals.
    """
    ds = date_str or date.today().isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", ds):
        return f"⚠️ Invalid date format: '{date_str}'. Use YYYY-MM-DD, e.g. '2026-06-22'."
    if int(ds[:4]) < 2026:
        return "⚠️ System records start from 2026. Is year ka data exist nahi karta."
    return get_date_status(ds)
