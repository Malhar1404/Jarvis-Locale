import pytest

from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.volume import get_volume, set_volume


def test_tools_are_auto_tier():
    assert get_risk_tier(get_volume) == RiskTier.AUTO
    assert get_risk_tier(set_volume) == RiskTier.AUTO


def test_set_volume_rejects_out_of_range():
    with pytest.raises(ValueError, match="between 0 and 100"):
        set_volume.invoke({"level": 150})


def test_get_and_set_round_trip():
    original = get_volume.invoke({})
    try:
        set_volume.invoke({"level": 33})
        assert get_volume.invoke({}) == 33
    finally:
        set_volume.invoke({"level": original})
