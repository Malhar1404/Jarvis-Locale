# The desk and floating panels

**One line:** a window with no layout, where children are placed by hand so they can be dragged anywhere.

## Why it exists
Layouts (`QVBoxLayout`, ...) decide where widgets go and resize them to fit. That is the opposite of
"a panel that stays wherever I dropped it". So the HUD's main widget (the *desk*) has no layout:
it paints its own background and places children itself.

## How it works
- `paintEvent`: draw the background (a cached pixmap) and a glow around each visible panel.
- `resizeEvent`: re-place the pieces that are fixed to the screen (top bar, reactor, dock) and
  keep panels inside the window.
- **Z-order** = creation order. `panel.raise_()` would cover the dock and the cursor, so the desk
  re-raises those two whenever a panel is raised (`_keep_overlays_on_top`).
- **Dragging in three steps**, shared by the mouse and the hand cursor:
  1. `begin_drag(point)`: store `offset = point - panel.pos()`
  2. `drag_to(point)`: `panel.move(point - offset)` (clamped to the desk)
  3. `end_drag()`: forget the offset
- The cursor overlay is `WA_TransparentForMouseEvents`, so `childAt()` looks straight through it.

## Small example
```python
panel.begin_drag(QPoint(300, 120))   # grabbed 40 px right of the panel's left edge
panel.drag_to(QPoint(500, 220))      # panel is now at (460, ...)  - the grabbed spot followed
panel.end_drag()
```

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Layouts (`QVBoxLayout`) | normal forms that resize | they fight free dragging |
| `QDockWidget` | docking/floating for free | looks like Windows chrome, hard to make HUD-like |
| `QGraphicsScene` + items | many movable items, built-in drag | mixing with normal widgets (text boxes) is awkward |
| QML / Qt Quick | smooth animated UIs on the GPU | a new language; would rewrite most of the UI |
| Each panel its own frameless window | panels over the real desktop, across monitors | more code (snap, focus, z-order); we chose one dark screen |

## Related
- [[qt-threading]]
- [[pinch-click-vs-drag]]
- [[phase-07b-hud]]
