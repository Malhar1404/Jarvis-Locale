"""Two tiny, harmless tools used to learn tool calling (Phase 1)."""

from datetime import datetime

from langchain_core.tools import tool


@tool
def get_time() -> str:
    """Get the current local date and time."""
    return datetime.now().strftime("%A, %d %B %Y, %H:%M")


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two whole numbers and return the result."""
    return a * b
