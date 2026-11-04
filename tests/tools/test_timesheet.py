from unittest.mock import MagicMock, patch

import gspread

from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.timesheet import add_timesheet_entry, list_timesheet_tabs, read_timesheet_tab


def test_list_timesheet_tabs_is_ask_once():
    assert get_risk_tier(list_timesheet_tabs) == RiskTier.ASK_ONCE


def test_list_timesheet_tabs_returns_tab_names():
    fake_sheet = MagicMock()
    tabs = [MagicMock(title="Guidelines"), MagicMock(title="Individual-Level")]
    fake_sheet.worksheets.return_value = tabs
    with patch("jarvis.tools.timesheet._open_timesheet", return_value=fake_sheet):
        result = list_timesheet_tabs.invoke({})
    assert result == "Guidelines\nIndividual-Level"


def test_list_timesheet_tabs_handles_no_tabs():
    fake_sheet = MagicMock()
    fake_sheet.worksheets.return_value = []
    with patch("jarvis.tools.timesheet._open_timesheet", return_value=fake_sheet):
        assert "no tabs found" in list_timesheet_tabs.invoke({})


def test_read_timesheet_tab_is_always_ask():
    assert get_risk_tier(read_timesheet_tab) == RiskTier.ALWAYS_ASK


def test_read_timesheet_tab_returns_rows():
    fake_worksheet = MagicMock()
    fake_worksheet.get_all_values.return_value = [
        ["Date", "Task", "Hours"],
        ["10/30/2026", "Fixed bug", "3"],
    ]
    fake_sheet = MagicMock()
    fake_sheet.worksheet.return_value = fake_worksheet
    with patch("jarvis.tools.timesheet._open_timesheet", return_value=fake_sheet):
        result = read_timesheet_tab.invoke({"tab_name": "Individual-Level"})
    assert result == "Date | Task | Hours\n10/30/2026 | Fixed bug | 3"


def test_read_timesheet_tab_unknown_tab_lists_known_ones():
    fake_sheet = MagicMock()
    fake_sheet.worksheet.side_effect = gspread.WorksheetNotFound
    fake_sheet.worksheets.return_value = [MagicMock(title="Guidelines")]
    with patch("jarvis.tools.timesheet._open_timesheet", return_value=fake_sheet):
        result = read_timesheet_tab.invoke({"tab_name": "Nope"})
    assert "No tab called 'Nope'" in result
    assert "Guidelines" in result


def test_add_timesheet_entry_is_always_ask():
    assert get_risk_tier(add_timesheet_entry) == RiskTier.ALWAYS_ASK


def test_add_timesheet_entry_inserts_at_row_2_with_mirrored_columns():
    fake_worksheet = MagicMock()
    fake_sheet = MagicMock()
    fake_sheet.worksheet.return_value = fake_worksheet
    with patch("jarvis.tools.timesheet._open_timesheet", return_value=fake_sheet):
        result = add_timesheet_entry.invoke(
            {"date": "10/31/2026", "task": "Fixed bug", "project": "sklo", "hours": "3"}
        )
    fake_worksheet.insert_row.assert_called_once_with(
        ["10/31/2026", "Fixed bug", "", "sklo", "3"], index=2
    )
    assert "10/31/2026" in result
