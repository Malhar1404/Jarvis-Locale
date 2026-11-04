from unittest.mock import MagicMock, patch

from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.timesheet import list_timesheet_tabs


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
