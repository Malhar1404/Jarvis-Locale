"""Google Sheets access for the user's daily timesheet.

Scoped to exactly ONE spreadsheet ID (jarvis.config.TIMESHEET_SPREADSHEET_ID) - never an
arbitrary ID the model might pass in. This is the external-resource equivalent of the local
folder allowlist: the tool itself only ever knows how to reach this one sheet.

list_timesheet_tabs is ASK_ONCE: this is the agent's first tool reaching a real external account
over the network, a new category of risk beyond local files/OS calls - worth a confirmation even
for a read. read_timesheet_tab is ALWAYS_ASK: it exposes real row content (actual work entries),
more sensitive than just tab names, every single time.
"""

import gspread
from google.oauth2.service_account import Credentials
from langchain_core.tools import tool

from jarvis.config import (
    GOOGLE_SERVICE_ACCOUNT_PATH,
    TIMESHEET_SPREADSHEET_ID,
    TIMESHEET_TAB_NAME,
)
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


@risk_tier(RiskTier.ALWAYS_ASK)
@tool
def add_timesheet_entry(date: str, task: str, project: str, hours: str) -> str:
    """Add one piece of work to the user's daily timesheet for a given date.

    The sheet holds ONE row per day: if an entry for this date already exists, the new
    task/project/hours are merged into that same row instead of creating a second row for the
    same date - call this once per project worked on; multiple calls for the same date combine
    correctly into a single row, matching the sheet's existing style.

    date: the day this entry is for, matching the sheet's existing format (e.g. "10/31/2026").
    task: what was worked on.
    project: the project name for this piece of work (e.g. "sklo").
    hours: hours spent on this piece of work (e.g. "3").
    """
    sheet = _open_timesheet()
    worksheet = sheet.worksheet(TIMESHEET_TAB_NAME)
    values = worksheet.get_all_values()
    row_index = next((i for i, row in enumerate(values) if row and row[0] == date), None)

    if row_index is None:
        # Column layout mirrors every existing row exactly: Date, task, (empty), Project, Hours.
        worksheet.insert_row([date, task, "", project, hours], index=2)
        return f"Added a new entry for {date} at the top of {TIMESHEET_TAB_NAME}."

    existing = values[row_index]
    existing_task = existing[1] if len(existing) > 1 else ""
    existing_project = existing[3] if len(existing) > 3 else ""
    existing_hours = existing[4] if len(existing) > 4 else ""

    merged_task = f"{existing_task}\n\n{task}" if existing_task else task
    merged_project = f"{existing_project}, {project}" if existing_project else project
    merged_hours = f"{existing_hours},{hours}" if existing_hours else hours

    sheet_row = row_index + 1  # gspread rows are 1-indexed
    worksheet.update(
        [[date, merged_task, "", merged_project, merged_hours]], f"A{sheet_row}:E{sheet_row}"
    )
    return f"Merged '{project}' into the existing entry for {date}."
