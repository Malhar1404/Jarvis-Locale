"""A recorded hand-tracking session: just numbers, never video or images.

Each camera frame becomes one HandFrame - when it was captured and the 21 hand landmarks MediaPipe
found in it (or None when no hand was seen). A recording can be replayed through the cursor
filter and the pinch detector without a camera or a raised arm, which is how they get tuned and
tested.

Coordinates are as MediaPipe reports them for the *mirrored* camera image (the tracker flips the
frame before detection):
    landmarks  x, y in 0..1 across the image (left to right, top to bottom); z is relative depth
    world      x, y, z in metres with the origin at the hand's centre - real size, so it does not
               change when the hand moves toward or away from the camera
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

LANDMARK_COUNT = 21


@dataclass(frozen=True)
class HandFrame:
    t: float  # seconds (time.monotonic() while tracking; starts at 0 in a saved recording)
    landmarks: np.ndarray | None  # shape (21, 3), or None when no hand was found
    world: np.ndarray | None  # shape (21, 3), or None


def save_recording(path: Path, frames: list[HandFrame]) -> None:
    """Write frames to a compressed .npz. Missing hands are stored as NaN rows."""
    count = len(frames)
    shape = (count, LANDMARK_COUNT, 3)
    image = np.full(shape, np.nan, dtype=np.float32)
    world = np.full(shape, np.nan, dtype=np.float32)
    times = np.array([frame.t for frame in frames], dtype=np.float64)
    if count:
        times -= times[0]  # only the gaps between frames matter, not the absolute clock
    for i, frame in enumerate(frames):
        if frame.landmarks is not None:
            image[i] = frame.landmarks
        if frame.world is not None:
            world[i] = frame.world
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, t=times, landmarks=image, world=world)


def load_recording(path: Path) -> list[HandFrame]:
    with np.load(path) as data:  # plain arrays only: no pickle, so a bad file can't run code
        times, image, world = data["t"], data["landmarks"], data["world"]
    return [
        HandFrame(
            t=float(times[i]),
            landmarks=None if np.isnan(image[i]).any() else image[i],
            world=None if np.isnan(world[i]).any() else world[i],
        )
        for i in range(len(times))
    ]
