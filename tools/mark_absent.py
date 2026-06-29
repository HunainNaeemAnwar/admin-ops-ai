from datetime import date
from typing import Optional

from agents import function_tool
from services.production_tools import (
    mark_absent as mark_worker_absent,
    mark_all_absent as mark_all_workers_absent,
)


@function_tool
def mark_absent_tool(workers: str, date_str: Optional[str] = None, reason: Optional[str] = None) -> str:
    """Mark one or all workers absent for a date.

    Args:
        workers: Worker name or 'all' for everyone
        date_str: Date YYYY-MM-DD (default: today)
        reason: Reason like 'Eid', 'sick'

    Returns:
        Confirmation message.
    """
    ds = date_str or date.today().isoformat()
    rsn = reason or ""
    if workers.lower() == "all":
        return mark_all_workers_absent(ds, rsn)
    return mark_worker_absent(workers, ds, rsn)
