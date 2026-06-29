from agents import function_tool
from services.report_tools import get_catalog


@function_tool
def list_catalog_tool() -> str:
    """List all workers, products, and today's status.

    Returns:
        Worker list, product rates, and current date.
    """
    return get_catalog()
