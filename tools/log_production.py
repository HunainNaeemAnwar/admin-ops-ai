import json

from agents import function_tool
from services.production_tools import record_production_batch


@function_tool
async def log_production_tool(entries_json: str) -> str:
    """Record production entries from JSON data.

    Accepts worker name, product code, quantity, and optional date.
    "sab" / "sab ny" = all 8 workers with same product/quantity.
    Past dates: include "date":"YYYY-MM-DD" in each entry.

    Args:
        entries_json: JSON array. Format: [{"worker":"Kaleem","product_code":"NUT","quantity":300}]

    Returns:
        Confirmation per entry.
    """
    try:
        entries = json.loads(entries_json) if isinstance(entries_json, str) else entries_json
        if isinstance(entries, dict):
            entries = [entries]
        if not isinstance(entries, list):
            return "Must be a JSON array"
        for entry in entries:
            date_str = entry.get("date", "")
            if date_str:
                year = int(date_str[:4])
                if year < 2026:
                    return f"⚠️ System records start from 2026. Cannot log data for year {year}."
        return await record_production_batch(entries)
    except (json.JSONDecodeError, TypeError):
        return "Invalid JSON format."
