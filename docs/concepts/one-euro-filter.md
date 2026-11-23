# One Euro filter (a steady cursor without lag)

**One line:** smoothing whose strength follows your speed - heavy when you are slow or still, light when you flick.

## Why it exists
One fixed amount of smoothing is a bad deal: smooth a lot and the cursor lags when you move;
smooth a little and it shakes when you hold still. Hand-tracking landmarks wobble by a few pixels
(we measured ~3 px at 2x gain on a 1440 px screen) - enough to miss a small button.

## How it works (`vision/pointer.py`)
```
cutoff = min_cutoff + beta * speed        # speed = how fast the point moves (px/s)
alpha  = 1 / (1 + tau/dt),  tau = 1/(2*pi*cutoff)
output = output + (new_sample - output) * alpha
```
- `min_cutoff` (Hz): lower = steadier when still (but slower to settle). We use 1.0.
- `beta`: higher = lag disappears sooner when you speed up (but more shake). We use **0.004**.
- `dt` is the **real time between camera samples**, so the result is the same at 30 or 60 fps.
- Speed is the length of the 2D velocity: x and y share one cutoff (separate filters would bend diagonals).
- A pause longer than 0.5 s (hand left the view) **restarts** the filter: the cursor appears at the hand.
- The same or an older timestamp is ignored.

Sensitivity is separate: `map_to_screen` maps only the camera region 0.25..0.75 to the whole screen
(**2x gain**). More gain also multiplies shake, so the filter works on *screen pixels after* the gain.

### What our data taught us
With `beta = 0.02` only 6-16% of the shake went away: camera noise *itself* looked like fast motion,
so the cutoff kept opening. At `0.004`: 31-62% removed with 31-62 ms lag. **How to tune:** set `beta`
to 0, lower `min_cutoff` until still jitter is fine, then raise `beta` until lag is fine.

## Small example
```python
f = OneEuroFilter2D(min_cutoff=1.0, beta=0.004)
x, y = f(raw_x, raw_y, t)      # call once per NEW camera sample, with its capture time
```

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Fixed smoothing (EMA) | simplest | one speed for all: laggy or shaky |
| Moving average | easy to explain | adds lag, never adapts |
| Dead zone (ignore moves < N px) | kills tiny shake | cursor freezes then jumps (we had this first) |
| "Leash" (move only when farther than r px) | bounded shake | no gain on our data: camera jitter was already small |
| Kalman filter | predicting motion | lots of tuning; overkill here |
| Mouse-style acceleration | relative pointing (trackpad) | with absolute pointing it drifts away from your hand |
| Steadier landmark (palm centre) | less jitter (2.4 vs 3.0 px) | loses the fingertip movement you wanted |

## Related
- [[pinch-click-vs-drag]]
- [[testing-with-recorded-data]]
- [[phase-07b-hud]]
