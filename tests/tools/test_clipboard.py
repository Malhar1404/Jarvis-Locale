from jarvis.safety.tiers import RiskTier, get_risk_tier
from jarvis.tools.clipboard import get_clipboard, set_clipboard


def test_tier_asymmetry():
    # Reading the clipboard can expose something the user copied privately; writing cannot.
    assert get_risk_tier(get_clipboard) == RiskTier.ASK_ONCE
    assert get_risk_tier(set_clipboard) == RiskTier.AUTO


def test_set_then_get_round_trip():
    original = get_clipboard.invoke({})
    try:
        set_clipboard.invoke({"text": "jarvis clipboard test"})
        assert get_clipboard.invoke({}) == "jarvis clipboard test"
    finally:
        if original != "(clipboard is empty or does not contain text)":
            set_clipboard.invoke({"text": original})
