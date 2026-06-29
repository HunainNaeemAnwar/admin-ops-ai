from typing import Optional

from agents import function_tool
from services.advance_tools import record_worker_advance


@function_tool
def record_advance_tool(worker: str, amount: float, year: int, month: int, description: Optional[str] = None) -> str:
    """Record advance payment to a worker.

    Args:
        worker: Worker name
        amount: Amount in rupees
        year: Year
        month: Month 1-12
        description: Optional reason

    Returns:
        Confirmation with monthly total.
    """
    return record_worker_advance(worker, amount, year, month, description or "")
