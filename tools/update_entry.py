from typing import Optional

from agents import function_tool
from services.production_tools import update_entry as update_production_entry
from services.database import get_logs_for_date


@function_tool
def update_entry_tool(entry_id: int = 0, new_quantity: int = 0, reason: Optional[str] = None,
                       worker: Optional[str] = None, product_code: Optional[str] = None,
                       date_str: Optional[str] = None) -> str:
    """Update an existing production entry.

    Provide worker + product_code + date_str for auto-lookup, or entry_id directly.

    Args:
        entry_id: Entry ID (0 = auto-lookup via worker/product_code/date_str)
        new_quantity: New quantity (must be positive)
        reason: Reason for change
        worker: Worker name for auto-lookup
        product_code: Product code for auto-lookup
        date_str: Date YYYY-MM-DD for auto-lookup

    Returns:
        Old vs new confirmation.
    """
    actual_id = entry_id

    if not actual_id or actual_id <= 0:
        if not worker or not product_code or not date_str:
            return "Give entry_id OR provide worker, product_code, and date_str for lookup."
        rows = get_logs_for_date(date_str)
        match = None
        for r in rows:
            if r["worker_name"].lower() == worker.lower() and r["product_code"].upper() == product_code.upper():
                match = r
                break
        if not match:
            return f"No {worker} / {product_code} entry found for {date_str}."
        actual_id = match["id"]

    return update_production_entry(actual_id, new_quantity, reason or "")
