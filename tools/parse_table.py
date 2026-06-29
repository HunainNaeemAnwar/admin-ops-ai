from agents import function_tool
from services.production_tools import parse_table_to_production as parse_table


@function_tool
def parse_table_tool(worker: str, table_text: str) -> str:
    """Parse a multi-row ASCII production table and record all entries.

    Handles box-drawing characters and pipe tables.
    Supports YYYY-MM-DD, MM-DD-YYYY, and DD-MM-YYYY date formats.

    Args:
        worker: Worker name (e.g. 'Naeem')
        table_text: Raw table text including pipe/border characters

    Returns:
        Per-date confirmation of recorded entries.
    """
    return parse_table(worker, table_text)
