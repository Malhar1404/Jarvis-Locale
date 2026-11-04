from unittest.mock import patch

from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.apps import open_app


def test_open_app_is_ask_once():
    assert get_risk_tier(open_app) == RiskTier.ASK_ONCE


def test_unknown_app_returns_error_text_not_a_crash():
    result = open_app.invoke({"name": "totally_not_a_real_app"})
    assert "Unknown app" in result


def test_known_app_launches_the_mapped_executable():
    with patch("jarvis.tools.apps.subprocess.Popen") as mock_popen:
        result = open_app.invoke({"name": "Notepad"})
    mock_popen.assert_called_once_with(["notepad.exe"])
    assert "Opened" in result
