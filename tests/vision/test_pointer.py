import math

import numpy as np
import pytest

from jarvis.vision.pointer import OneEuroFilter2D, map_to_screen


def test_map_to_screen_centre_edges_and_clamp():
    assert map_to_screen((0.5, 0.5), 1000, 500, 0.25, 0.75) == (500, 250)
    assert map_to_screen((0.25, 0.75), 1000, 500, 0.25, 0.75) == (0, 500)
    assert map_to_screen((0.0, 1.0), 1000, 500, 0.25, 0.75) == (0, 500)  # outside: clamped


def test_map_to_screen_gain_is_two_for_a_half_wide_region():
    x1, _ = map_to_screen((0.5, 0.5), 1000, 1000, 0.25, 0.75)
    x2, _ = map_to_screen((0.55, 0.5), 1000, 1000, 0.25, 0.75)
    assert x2 - x1 == pytest.approx(0.05 * 2 * 1000)


def test_holding_still_removes_most_of_the_shake():
    rng = np.random.default_rng(1)
    filt = OneEuroFilter2D()
    sigma = 3.0  # px of landmark noise
    outputs = []
    for i in range(300):
        x, y = 500 + rng.normal(0, sigma), 300 + rng.normal(0, sigma)
        outputs.append(filt(x, y, i / 30))
    steady = np.array(outputs[60:])
    assert steady[:, 0].std() < 0.6 * sigma
    assert steady[:, 1].std() < 0.6 * sigma
    assert abs(steady[:, 0].mean() - 500) < 1.5  # it smooths, it does not drift


def test_a_fast_flick_has_almost_no_lag():
    filt = OneEuroFilter2D()
    speed = 2000.0  # px/s
    for i in range(31):
        t = i / 30
        x, _ = filt(speed * t, 0.0, t)
    assert abs(x - speed * 1.0) < 40  # within ~1 frame of the true position at 2000 px/s


def test_a_slow_move_is_followed_without_big_lag():
    filt = OneEuroFilter2D()
    for i in range(61):
        t = i / 30
        x, _ = filt(50.0 * t, 0.0, t)  # 50 px/s: slow and careful
    assert abs(x - 100.0) < 25


def test_result_does_not_depend_on_the_sample_rate():
    def run(rate: int) -> float:
        filt = OneEuroFilter2D()
        out = (0.0, 0.0)
        for i in range(int(2 * rate) + 1):
            t = i / rate
            out = filt(100 * math.sin(2 * math.pi * 0.5 * t), 0.0, t)
        return out[0]

    assert run(30) == pytest.approx(run(60), abs=4.0)


def test_a_long_gap_restarts_the_filter_at_the_new_point():
    filt = OneEuroFilter2D()
    filt(0.0, 0.0, 0.0)
    assert filt(900.0, 500.0, 5.0) == (900.0, 500.0)  # hand reappeared: no sliding in from 0,0


def test_a_repeated_or_older_timestamp_changes_nothing():
    filt = OneEuroFilter2D()
    filt(0.0, 0.0, 1.0)
    first = filt(10.0, 0.0, 1.1)
    assert filt(99.0, 99.0, 1.1) == first
    assert filt(99.0, 99.0, 0.5) == first


def test_reset_forgets_everything():
    filt = OneEuroFilter2D()
    filt(0.0, 0.0, 0.0)
    filt(10.0, 0.0, 0.03)
    filt.reset()
    assert filt(700.0, 700.0, 0.06) == (700.0, 700.0)
