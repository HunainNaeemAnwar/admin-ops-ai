from datetime import date
from typing import Optional

from agents import function_tool
from services.report_tools import get_production_summary


@function_tool
def get_summary_tool(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Production summary for a period.

    Args:
        period: 'daily', 'weekly', or 'monthly'
        year: Year (default: current)
        month: Month 1-12 (default: current)
        day: Day 1-31 (default: today)

    Returns:
        Summary with product totals per worker.
    """
    today = date.today()
    y = year or today.year
    if y < 2026:
        return "⚠️ System records start from 2026. Please select year >= 2026."
    return get_production_summary(period, y, month or today.month, day or today.day)
