"""Google Sheets access for the user's daily timesheet.

Scoped to exactly ONE spreadsheet ID (jarvis.config.TIMESHEET_SPREADSHEET_ID) - never an
arbitrary ID the model might pass in. This is the external-resource equivalent of the local
folder allowlist: the tool itself only ever knows how to reach this one sheet.

ASK_ONCE: this is the agent's first tool that reaches a real external account over the network,
a new category of risk beyond local files/OS calls - worth a confirmation, even for a read.
"""

import gspread
from google.oauth2.service_account import Credentials
from langchain_core.tools import tool

from jarvis.config import GOOGLE_SERVICE_ACCOUNT_PATH, TIMESHEET_SPREADSHEET_ID
from jarvis.safety.tiers import RiskTier, risk_tier

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _open_timesheet():
    creds = Credentials.from_service_account_file(str(GOOGLE_SERVICE_ACCOUNT_PATH), scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(TIMESHEET_SPREADSHEET_ID)


@risk_tier(RiskTier.ASK_ONCE)
@tool
def list_timesheet_tabs() -> str:
    """List the tab (worksheet) names in the user's timesheet Google Sheet."""
    sheet = _open_timesheet()
    names = [ws.title for ws in sheet.worksheets()]
    return "\n".join(names) if names else "(no tabs found)"


MAX_PREVIEW_ROWS = 5


@risk_tier(RiskTier.ALWAYS_ASK)
@tool
def read_timesheet_tab(tab_name: str) -> str:
    """Read the header row and first few entries of one tab in the user's timesheet Google Sheet."""
    sheet = _open_timesheet()
    try:
        worksheet = sheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        known = ", ".join(ws.title for ws in sheet.worksheets())
        return f"No tab called '{tab_name}'. Known tabs: {known}."

    rows = worksheet.get_all_values()[:MAX_PREVIEW_ROWS]
    if not rows:
        return "(tab is empty)"
    return "\n".join(" | ".join(row) for row in rows)
