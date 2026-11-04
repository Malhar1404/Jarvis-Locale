"""Read and write the system clipboard, via pywin32 (already installed - pulled in by pycaw).

get_clipboard is ASK_ONCE, not AUTO: unlike volume/brightness, clipboard content can be
something the user copied privately (a password, a token) and never meant to hand to the model.
set_clipboard is AUTO: writing is low risk and instantly visible/reversible.
"""

import win32clipboard
from langchain_core.tools import tool

from jarvis.safety.tiers import RiskTier, risk_tier


@risk_tier(RiskTier.ASK_ONCE)
@tool
def get_clipboard() -> str:
    """Get the current text content of the system clipboard."""
    win32clipboard.OpenClipboard()
    try:
        if not win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            return "(clipboard is empty or does not contain text)"
        return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()


@risk_tier(RiskTier.AUTO)
@tool
def set_clipboard(text: str) -> str:
    """Set the system clipboard's text content."""
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text)
    finally:
        win32clipboard.CloseClipboard()
    return "Clipboard updated."
