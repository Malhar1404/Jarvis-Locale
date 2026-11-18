from types import SimpleNamespace

import pytest

from jarvis.vision.hand_tracking import INDEX_TIP, THUMB_TIP, is_pinching, pinch_ratio


def _hand(gap: float):
    """21 landmarks: wrist at (0,0), middle knuckle 1.0 away, thumb/index tips `gap` apart."""
    points = [SimpleNamespace(x=0.0, y=0.0) for _ in range(21)]
    points[9] = SimpleNamespace(x=0.0, y=1.0)
    points[THUMB_TIP] = SimpleNamespace(x=0.5, y=0.5)
    points[INDEX_TIP] = SimpleNamespace(x=0.5 + gap, y=0.5)
    return points


def test_pinch_ratio_is_measured_in_palm_sizes():
    assert pinch_ratio(_hand(0.2)) == pytest.approx(0.2)


def test_pinch_uses_hysteresis():
    assert is_pinching(0.2, was_pinching=False)
    assert not is_pinching(0.38, was_pinching=False)  # not close enough to start
    assert is_pinching(0.38, was_pinching=True)  # but close enough to keep holding
    assert not is_pinching(0.6, was_pinching=True)
