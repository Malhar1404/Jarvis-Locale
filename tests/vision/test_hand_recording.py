import numpy as np

from jarvis.vision.hand_recording import HandFrame, load_recording, save_recording


def _points(offset: float) -> np.ndarray:
    return (np.arange(63, dtype=np.float32).reshape(21, 3) + offset) / 100


def test_round_trip_keeps_numbers_and_missing_hands(tmp_path):
    frames = [
        HandFrame(10.0, _points(0), _points(1)),
        HandFrame(10.033, None, None),  # no hand in this frame
        HandFrame(10.066, _points(2), None),  # image landmarks but no world landmarks
    ]
    path = tmp_path / "take.npz"

    save_recording(path, frames)
    loaded = load_recording(path)

    assert [round(f.t, 3) for f in loaded] == [0.0, 0.033, 0.066]  # starts at 0
    assert np.allclose(loaded[0].landmarks, frames[0].landmarks)
    assert np.allclose(loaded[0].world, frames[0].world)
    assert loaded[1].landmarks is None and loaded[1].world is None
    assert loaded[2].world is None
    assert np.allclose(loaded[2].landmarks, frames[2].landmarks)


def test_an_empty_recording_round_trips(tmp_path):
    path = tmp_path / "empty.npz"
    save_recording(path, [])
    assert load_recording(path) == []
