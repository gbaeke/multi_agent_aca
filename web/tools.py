from agents import function_tool, WebSearchTool
from datetime import datetime


@function_tool
def get_current_date() -> str:
    """Get the current date."""
    return f"The current date is {datetime.now().strftime('%Y-%m-%d')}"


# keep a dictionary of tools
all_tools = {
    "get_current_date": get_current_date,
    "web_search": WebSearchTool(), # requires WebSearchTool import
}


