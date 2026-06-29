import json
from typing import Optional

from agents import function_tool
from services.production_tools import (
    record_production_batch,
    mark_absent as mark_worker_absent,
)


@function_tool
async def batch_daily_update_tool(entries_json: str, absent_workers: Optional[str] = None) -> str:
    """Record production and mark absences in one call.

    Args:
        entries_json: JSON array. Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]
        absent_workers: JSON array of worker names to mark absent, or null.

    Returns:
        Combined results.
    """
    results = []
    try:
        parsed = json.loads(entries_json) if isinstance(entries_json, str) else entries_json
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            results.append("[Production] Invalid: must be an array")
        else:
            results.append(f"[Production]\n{await record_production_batch(parsed)}")
    except (json.JSONDecodeError, TypeError) as e:
        results.append(f"[Production] Invalid JSON: {e}")

    if absent_workers:
        try:
            absent_list = json.loads(absent_workers) if isinstance(absent_workers, str) else absent_workers
            if isinstance(absent_list, str):
                absent_list = [absent_list]
            for w in absent_list:
                if isinstance(w, str) and w.strip():
                    results.append(mark_worker_absent(w.strip()))
        except (json.JSONDecodeError, TypeError) as e:
            results.append(f"[Absent] Invalid input: {e}")

    return "\n\n".join(results) if results else "No operations performed."
