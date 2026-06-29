from datetime import date
from typing import Optional

from agents import function_tool
from services.email_tools import send_summary


@function_tool
def send_report_tool(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    """Email production summary to the manager.

    Args:
        period: 'daily', 'weekly', or 'monthly'
        year: Year (default: current)
        month: Month 1-12 (default: current)
        day: Day 1-31 (default: today)

    Returns:
        Delivery status.
    """
    today = date.today()
    return send_summary(period, year or today.year, month or today.month, day or today.day)
