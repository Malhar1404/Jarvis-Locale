# Pinch: click vs drag

**One line:** decide click or drag by *what is under the cursor when the fingers start closing*, never by how far the hand moved.

## Why it exists
The cursor follows the point between thumb tip and index tip. When you pinch, those tips move
toward each other, so **the cursor drifts 30-50 px on its own** (we measured it). A rule like
"moved more than 12 px = drag" turned every tap over a panel into a drag, and a button inside a
panel counted as part of the panel.

## How it works (`vision/pinch.py`, pure code, no Qt)
**1. Is it pinched?** `PinchDetector`: ratio = thumb-index gap / palm size (about 1.0 open, under 0.3 pinched).
- Hysteresis: start below **0.30**, end only above **0.45** (one threshold would flicker).
- Debounce: **2 camera frames in a row** to switch, so one noisy frame can't click or drop a drag.

**2. When did the fingers start to close?** `closing_onset()` = the last frame still near fully open.
Same idea for `opening_onset()` on the way out.

**3. Position history.** Keep the last ~1 s of cursor positions.
- Aim point (click/grab) = position at `closing_onset`.
- Drop point = position at `opening_onset`.

**4. Rules by target** (asked once, at press, at the aim point):
| Under the cursor | Quick pinch | Pinch, hold, move |
|---|---|---|
| button / text field | click | nothing (never drags) |
| panel (title bar or body) | raise it ("tap") | drag it |
| anything else | nothing | nothing |

**5. Details.** Drag starts after 14 px measured from where the pinch *closed* (not from the aim
point), so closing drift can't start it and the panel never jumps. A click needs: held <= 0.8 s,
and the cursor within 30 px of where the pinch closed. Tracking lost > 0.15 s mid-pinch: cancel,
restore the panel, never click.

## Small example
```python
inter = PinchInteraction(classify)          # classify(pos) -> ("button" | "field" | "panel" | "none", widget)
for t, pos, ratio in samples:               # one call per NEW camera sample
    for event in inter.update(t, pos, ratio):
        ...                                  # press, click, tap, drag_start, drag, drop, release, cancel
```

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Distance threshold (old way) | one simple rule | breaks on the closing drift |
| Time only (short = click, long = drag) | easy | slow drags and slow clicks both fail |
| Dwell click (hover to click) | no pinch needed | slow, accidental clicks |
| A different gesture for each (tap vs fist) | no ambiguity | harder to learn, camera must tell poses apart |
| Drag only from the title bar | matches the mouse | small target for a hand |
| MediaPipe 3D (world) pinch distance | independent of hand angle | noisy on first data (26 mm on a firm pinch); revisit |

## Related
- [[one-euro-filter]]
- [[hud-desk-and-floating-panels]]
- [[testing-with-recorded-data]]
- [[phase-07b-hud]]
