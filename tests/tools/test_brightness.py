import pytest

from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.brightness import get_brightness, set_brightness


def test_tools_are_auto_tier():
    assert get_risk_tier(get_brightness) == RiskTier.AUTO
    assert get_risk_tier(set_brightness) == RiskTier.AUTO


def test_set_brightness_rejects_out_of_range():
    with pytest.raises(ValueError, match="between 0 and 100"):
        set_brightness.invoke({"level": -5})


def test_get_and_set_round_trip():
    original = get_brightness.invoke({})
    try:
        set_brightness.invoke({"level": 60})
        assert get_brightness.invoke({}) == 60
    finally:
        set_brightness.invoke({"level": original})
