"""Mind: the "internal processing" panel - a step-by-step trace of the CURRENT request only.

It is built purely from AgentEvents (plus the UI's own clock for timings), so the agent never
knows this panel exists. Each step is a dot on a vertical line with a title, a time on the
right and an optional body. The newest step is "live": its time keeps counting until the next
step arrives.

Note on THINKING: qwen3:4b-instruct writes no hidden reasoning, so this step shows *that* the
model is working and for how long - not its thoughts. A visible plan step is a separate,
agent-side feature (see PLAN.md, Phase 7b step 6).
"""

import json
import time

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from jarvis.agent.events import ScreenShot
from jarvis.ui import theme
from jarvis.ui.hud.comms import make_scroll_column
from jarvis.ui.hud.style import TEXT_DIM, TIER_LABELS

THUMB_WIDTH = 176
QUICK_ROUTE_SECONDS = 0.3  # a "thinking" step shorter than this before a tool call was routing


class _Step(QWidget):
    def __init__(self, title: str, color: str, meta: str = "") -> None:
        super().__init__()
        self.kind = ""
        self.last = True  # the newest step has no line continuing below its dot
        self._color = QColor(color)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 0, 0, 14)
        layout.setSpacing(6)
        header = QHBoxLayout()
        header.setSpacing(8)
        title_label = QLabel(title, objectName="mindTitle")
        title_label.setStyleSheet(f"color: {color};")
        self._meta = QLabel(meta, objectName="mindMeta")
        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(self._meta)
        layout.addLayout(header)
        self._layout = layout

    def set_meta(self, text: str) -> None:
        self._meta.setText(text)

    def add_text(self, text: str, style: str = "mindText") -> QLabel:
        label = QLabel(text, objectName=style)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._layout.addWidget(label)
        return label

    def add_widget(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)

    def paintEvent(self, event) -> None:  # noqa: ARG002
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.last:
            line = QColor(self._color)
            line.setAlpha(80)
            p.setPen(line)
            p.drawLine(QPointF(6, 18), QPointF(6, self.height()))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(QPointF(6, 8), 5, 5)
        p.end()


def _format_args(args: dict) -> str:
    return ", ".join(f"{key}={value!r}" for key, value in args.items())


def _thumbnail(shot: ScreenShot) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    image = QLabel(objectName="thumb")
    pixmap = QPixmap(shot.path)
    if pixmap.isNull():
        image.setText("image unavailable")
        image.setStyleSheet(f"color: {TEXT_DIM};")
        image.setFixedSize(THUMB_WIDTH, 99)
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
    else:
        image.setPixmap(
            pixmap.scaledToWidth(THUMB_WIDTH, Qt.TransformationMode.SmoothTransformation)
        )
    layout.addWidget(image)
    layout.addWidget(QLabel(shot.label, objectName="thumbCaption"))
    return box


class MindView(QWidget):
    def __init__(self, model: str, vision_model: str, tool_tiers: dict[str, str]) -> None:
        super().__init__()
        self._model = model
        self._vision_model = vision_model
        self._tiers = tool_tiers
        scroll, self._column = make_scroll_column()
        self._footer = QLabel("waiting for a request", objectName="mindFooter")

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(16, 8, 16, 10)
        footer_row.addWidget(self._footer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(scroll, 1)
        layout.addLayout(footer_row)

        self._steps: list[_Step] = []
        self._live: tuple[_Step, float] | None = None
        self._answer: _Step | None = None
        self._answer_label: QLabel | None = None
        self._tokens = 0
        self._vision_left = 0
        self._model_calls = 0
        self._tool_calls = 0
        self._started = 0.0
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick_live)
        self._clock.start(100)

    # -- step bookkeeping ----------------------------------------------------------------
    def _add(self, step: _Step, *, live: bool = False) -> _Step:
        if self._steps:
            self._steps[-1].last = False
            self._steps[-1].update()
        self._steps.append(step)
        self._column.insertWidget(self._column.count() - 1, step)
        if live:
            self._live = (step, time.monotonic())
        return step

    def _end_live(self) -> float:
        if self._live is None:
            return 0.0
        step, started = self._live
        elapsed = time.monotonic() - started
        step.set_meta(f"{elapsed:.1f}s")
        self._live = None
        return elapsed

    def _tick_live(self) -> None:
        if self._live is not None:
            step, started = self._live
            step.set_meta(f"{time.monotonic() - started:.1f}s")

    def _remove(self, step: _Step) -> None:
        self._steps.remove(step)
        self._column.removeWidget(step)
        step.deleteLater()
        if self._steps:
            self._steps[-1].last = True
            self._steps[-1].update()

    def _thinking(self) -> None:
        self._end_live()
        self._answer = None
        step = _Step(f"THINKING · {self._model}", theme.TOOL)
        step.kind = "thinking"
        self._model_calls += 1
        self._add(step, live=True)

    # -- called by the window, one per AgentEvent (plus request start / end) -------------
    def begin_request(self, text: str, *, voice: bool) -> None:
        for step in self._steps:
            self._column.removeWidget(step)
            step.deleteLater()
        self._steps.clear()
        self._live = None
        self._model_calls = self._tool_calls = 0
        self._started = time.monotonic()
        self._footer.setText("working…")
        heard = _Step("HEARD · whisper" if voice else "TYPED", TEXT_DIM)
        heard.add_text(f'"{text}"')
        self._add(heard)
        self._thinking()

    def token(self, text: str) -> None:
        if self._answer is None:
            self._end_live()
            self._answer = _Step("ANSWERING · streaming", theme.OK)
            self._answer_label = self._answer.add_text("", "mindMeta")
            self._tokens = 0
            self._add(self._answer, live=True)
        self._tokens += 1
        self._answer_label.setText(f"{self._tokens} tokens → Comms")

    def tool_call(self, name: str, args: dict) -> None:
        if self._live is not None and self._live[0].kind == "thinking":
            step, started = self._live
            if time.monotonic() - started < QUICK_ROUTE_SECONDS:
                # Deterministic routing (e.g. screen_intent) asked for this tool, not the model.
                self._live = None
                self._model_calls -= 1
                self._remove(step)
        self._end_live()
        self._answer = None
        self._tool_calls += 1
        tier = TIER_LABELS.get(self._tiers.get(name, ""), "")
        # The tier goes in the title: the right-hand slot is taken by the live timer.
        step = _Step(f"TOOL CALL · {tier}" if tier else "TOOL CALL", theme.TOOL)
        step.add_text(f"{name}({_format_args(args)})", "mindMono")
        self._add(step, live=True)

    def approval(self, name: str, tier: str) -> None:
        self._end_live()
        step = _Step("WAITING FOR YOU", theme.APPROVAL)
        step.add_text(f"{name} needs your OK ({TIER_LABELS.get(tier, tier)})")
        self._add(step, live=True)

    def approval_decided(self, decision: str) -> None:
        if self._live is not None:
            self._live[0].add_text("allowed" if decision == "yes" else "denied", "mindMeta")
        self._end_live()

    def screen_captured(self, shots: list[ScreenShot]) -> None:
        self._end_live()
        count = len(shots)
        step = _Step(f"SCREEN CAPTURED · {count} monitor{'s' if count != 1 else ''}", theme.ACCENT)
        grid_box = QWidget()
        grid = QGridLayout(grid_box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        for index, shot in enumerate(shots):
            grid.addWidget(_thumbnail(shot), index // 2, index % 2)
        step.add_widget(grid_box)
        self._add(step)
        self._vision_left = count
        self._add(self._vision_step(), live=True)

    def _vision_step(self) -> _Step:
        step = _Step(f"VISION · {self._vision_model}", theme.ACCENT)
        step.kind = "vision"
        return step

    def vision(self, label: str, text: str, seconds: float) -> None:
        if self._live is not None and self._live[0].kind == "vision":
            step = self._live[0]  # fill in the placeholder that has been counting up
            self._live = None
        else:
            step = self._add(self._vision_step())
        step.set_meta(f"{seconds:.1f}s")
        step.add_text(f"{label}: {text[:600]}", "mindBox")
        self._vision_left = max(0, self._vision_left - 1)
        if self._vision_left:
            self._add(self._vision_step(), live=True)

    def tool_result(self, name: str, content: str, status: str) -> None:
        self._end_live()
        if status != "ok":
            step = _Step("TOOL ERROR", theme.ERROR)
            step.add_text(content[:300], "mindMono")
            self._add(step)
        elif name != "inspect_screen":  # the screenshots + vision steps already show that one
            step = _Step("RESULT", theme.OK)
            step.add_text(_short_result(content), "mindMono")
            self._add(step)
        self._thinking()  # the model now reads the result

    def error(self, message: str) -> None:
        self._end_live()
        step = _Step("ERROR", theme.ERROR)
        step.add_text(message[:300], "mindMono")
        self._add(step)

    def done(self) -> None:
        self._end_live()
        total = time.monotonic() - self._started
        calls = f"{self._model_calls} model call{'s' if self._model_calls != 1 else ''}"
        tools = f"{self._tool_calls} tool{'s' if self._tool_calls != 1 else ''}"
        self._footer.setText(f"{calls} · {tools} · total {total:.1f}s")


def _short_result(content: str) -> str:
    """Tool results can be long or JSON; show a readable first slice."""
    try:
        content = json.dumps(json.loads(content), ensure_ascii=False)
    except (ValueError, TypeError):
        pass
    return content if len(content) <= 240 else content[:240] + "…"
