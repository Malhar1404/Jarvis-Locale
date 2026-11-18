import math

import pytest

from jarvis.vision.pinch import PinchDetector, PinchInteraction

DT = 1 / 30  # camera frame time


def lerp(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def pinch_sequence(start, drift=(0.0, 0.0), hold=6, move=(0.0, 0.0), move_frames=0):
    """Camera samples (pos, pinch_value) for: hand resting, fingers closing, holding (optionally
    moving), fingers opening, hand resting. While the fingers close the cursor drifts by `drift`
    and while they open it drifts back - like the real midpoint between thumb and index tip.
    """
    frames = [(start, 1.0)] * 15
    after_close = (start[0] + drift[0], start[1] + drift[1])
    for i, value in enumerate([0.75, 0.4, 0.1]):
        frames.append((lerp(start, after_close, (i + 1) / 3), value))
    frames += [(after_close, 0.1)] * hold
    end = after_close
    for i in range(move_frames):
        end = lerp(
            after_close, (after_close[0] + move[0], after_close[1] + move[1]), (i + 1) / move_frames
        )
        frames.append((end, 0.1))
    for i, value in enumerate([0.5, 0.9, 1.0]):
        frames.append((lerp(end, start, (i + 1) / 3), value))
    frames += [(start, 1.0)] * 10
    return frames


def run(frames, kind, t0=0.0):
    """Feed frames to a PinchInteraction whose every position is classified as `kind`."""
    interaction = PinchInteraction(lambda pos: (kind, "widget"))
    events = []
    for i, (pos, value) in enumerate(frames):
        events += interaction.update(t0 + i * DT, pos, value)
    return events


def kinds(events):
    return [event.kind for event in events]


def test_tap_on_a_button_clicks_even_though_the_cursor_drifts_while_closing():
    events = run(pinch_sequence((300, 200), drift=(40, 0)), "button")

    assert kinds(events) == ["press", "click", "release"]
    click = events[1]
    assert math.dist(click.pos, (300, 200)) < 2  # the aimed-at spot, not the drifted one


def test_a_button_never_drags_however_far_you_move():
    events = run(pinch_sequence((300, 200), hold=3, move=(200, 0), move_frames=15), "button")

    assert "drag_start" not in kinds(events)
    assert "click" not in kinds(events)  # you wandered off the button: not a click either


def test_closing_drift_alone_does_not_start_a_drag_on_a_panel():
    events = run(pinch_sequence((500, 300), drift=(40, 0)), "panel")

    assert kinds(events) == ["press", "tap", "release"]


def test_dragging_a_panel_starts_once_follows_and_drops_where_you_stopped():
    events = run(
        pinch_sequence((500, 300), drift=(40, 10), hold=3, move=(200, 0), move_frames=15), "panel"
    )

    assert kinds(events).count("drag_start") == 1
    assert kinds(events).count("drop") == 1
    assert "click" not in kinds(events) and "tap" not in kinds(events)
    assert kinds(events)[-1] == "release"
    drop = next(event for event in events if event.kind == "drop")
    assert math.dist(drop.pos, (740, 310)) < 6  # not the point the opening fingers drifted to
    start = next(event for event in events if event.kind == "drag_start")
    assert math.dist(start.pos, (540, 310)) < 25  # measured from where the pinch closed


def test_a_slow_hold_on_a_button_is_not_a_click():
    events = run(pinch_sequence((300, 200), hold=40), "button")  # ~1.3 s

    assert "click" not in kinds(events)


def test_a_pinch_on_empty_space_does_nothing():
    events = run(pinch_sequence((300, 200)), "none")

    assert kinds(events) == ["press", "release"]


def test_one_noisy_frame_cannot_start_a_pinch():
    frames = [((300, 200), 1.0)] * 10 + [((300, 200), 0.1)] + [((300, 200), 1.0)] * 10

    assert run(frames, "button") == []


def test_one_noisy_frame_cannot_end_a_pinch_in_the_middle_of_a_drag():
    frames = pinch_sequence((500, 300), hold=3, move=(200, 0), move_frames=15)
    index = 15 + 3 + 3 + 8  # a frame in the middle of the drag
    frames[index] = (frames[index][0], 0.7)  # fingers "open" for a single frame

    events = run(frames, "panel")

    assert kinds(events).count("drag_start") == 1
    assert kinds(events).count("drop") == 1  # still one single drag, not two


def test_two_quick_taps_are_two_clicks():
    first = pinch_sequence((300, 200), drift=(30, 0))
    second = pinch_sequence((300, 200), drift=(30, 0))

    events = run(first + second, "button")

    assert kinds(events).count("click") == 2


def test_cancel_mid_drag_ends_it_and_nothing_follows():
    interaction = PinchInteraction(lambda pos: ("panel", "widget"))
    frames = pinch_sequence((500, 300), hold=3, move=(200, 0), move_frames=15)
    events = []
    for i, (pos, value) in enumerate(frames[:30]):  # stop in the middle of the drag
        events += interaction.update(i * DT, pos, value)
    assert "drag_start" in kinds(events)

    cancelled = interaction.cancel()

    assert kinds(cancelled) == ["cancel"]
    assert interaction.update(31 * DT, (700, 300), 1.0) == []


def test_detector_finds_when_the_fingers_started_closing_and_opening():
    detector = PinchDetector()
    values = [1.0, 1.0, 1.0, 0.75, 0.4, 0.1, 0.1, 0.1, 0.1, 0.5, 0.9, 1.0]
    signals = [detector.update(i * DT, v) for i, v in enumerate(values)]

    assert signals.count("press") == 1 and signals.count("release") == 1
    press_at = signals.index("press")
    assert press_at == 6  # needs two frames below 0.3 in a row
    release_at = signals.index("release")
    assert release_at == 10  # needs two frames above 0.45 in a row

    # replay to the press / release frame to ask for the onsets
    d = PinchDetector()
    for i, v in enumerate(values[: press_at + 1]):
        d.update(i * DT, v)
    assert d.closing_onset() == pytest.approx(2 * DT)  # the last fully open frame
    for i, v in enumerate(values[press_at + 1 : release_at + 1], start=press_at + 1):
        d.update(i * DT, v)
    assert d.opening_onset() == pytest.approx(8 * DT)  # the last fully closed frame
