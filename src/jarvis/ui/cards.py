"""One widget per thing that happens in a turn - a user message, Jarvis's reply, a tool call,
a tool result, an error, or an approval request. This replaces a single text log so that an
approval request can carry real, clickable buttons, and a "thinking" state can animate.
"""

from html import escape

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from jarvis.ui import theme


class Card(QFrame):
    """A rounded panel with a colored left edge - the color is what tells cards apart at a
    glance (cyan = Jarvis, amber = tool call, green/red = result, magenta = approval).
    """

    def __init__(self, accent: str) -> None:
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet(
            "QFrame#card {"
            f"background-color: {theme.PANEL};"
            f"border-left: 3px solid {accent};"
            "border-radius: 4px;"
            "}"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(4)

    def _label(self, text: str, color: str, *, bold: bool = False) -> QLabel:
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)  # never parsed as HTML, even if it has "<"
        weight = "600" if bold else "400"
        label.setStyleSheet(
            f"color: {color}; font-weight: {weight}; font-family: {theme.MONO_FONT};"
            "font-size: 13px; background: transparent; border: none;"
        )
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._layout.addWidget(label)
        return label

    def _rich_label(self, color: str) -> QLabel:
        """A label we build with our own small, escaped HTML (for a bold header + body)."""
        label = QLabel()
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setStyleSheet(
            f"color: {color}; font-family: {theme.MONO_FONT}; font-size: 13px;"
            "background: transparent; border: none;"
        )
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._layout.addWidget(label)
        return label


class UserCard(Card):
    def __init__(self, text: str) -> None:
        super().__init__(theme.MUTED)
        label = self._rich_label(theme.TEXT)
        body = escape(text).replace("\n", "<br>")
        label.setText(f'<span style="color:{theme.MUTED};font-weight:600;">You</span><br>{body}')


class AssistantCard(Card):
    """Jarvis's reply, built up one streamed token at a time."""

    def __init__(self) -> None:
        super().__init__(theme.ACCENT)
        self._text = ""
        self._body_label = self._rich_label(theme.TEXT)
        self._render()

    def append_token(self, text: str) -> None:
        self._text += text
        self._render()

    def _render(self) -> None:
        header = f'<span style="color:{theme.ACCENT};font-weight:600;">Jarvis</span><br>'
        body = escape(self._text).replace("\n", "<br>")
        self._body_label.setText(header + body)


class ToolCallCard(Card):
    def __init__(self, name: str, args: dict) -> None:
        super().__init__(theme.TOOL)
        self._label(f"▸ {name}({args})", theme.TOOL)


class ToolResultCard(Card):
    def __init__(self, name: str, content: str, status: str) -> None:
        color = theme.OK if status == "ok" else theme.ERROR
        icon = "✓" if status == "ok" else "✗"
        super().__init__(color)
        self._label(f"{icon} {name} → {content[:200]}", color)


class ErrorCard(Card):
    def __init__(self, message: str) -> None:
        super().__init__(theme.ERROR)
        self._label(f"⚠ {message}", theme.ERROR)


class ApprovalCard(Card):
    """An inline Yes/No panel - the graph is paused until one of these buttons is clicked."""

    decided = Signal(str)  # "yes" or "no"

    def __init__(self, name: str, args: dict, tier: str) -> None:
        super().__init__(theme.APPROVAL)
        self._label(f"◈ approval needed: {name}({args})", theme.APPROVAL, bold=True)
        self._label(f"risk tier: {tier}", theme.MUTED)

        self._yes_button = QPushButton("Yes", objectName="approvalYes")
        self._no_button = QPushButton("No", objectName="approvalNo")
        self._yes_button.clicked.connect(lambda: self._decide("yes"))
        self._no_button.clicked.connect(lambda: self._decide("no"))

        button_row = QHBoxLayout()
        button_row.addWidget(self._yes_button)
        button_row.addWidget(self._no_button)
        button_row.addStretch()
        self._layout.addLayout(button_row)

    def _decide(self, decision: str) -> None:
        self._yes_button.setEnabled(False)
        self._no_button.setEnabled(False)
        self._label(f"you answered: {decision}", theme.MUTED)
        self.decided.emit(decision)


class ThinkingIndicator(QFrame):
    """A small bouncing-dots card shown while waiting for the model or a tool to finish."""

    _FRAMES = ["● · ·", "· ● ·", "· · ●"]

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self._label = QLabel(self._FRAMES[0])
        self._label.setStyleSheet(
            f"color: {theme.ACCENT}; font-family: {theme.MONO_FONT}; font-size: 13px;"
        )
        layout.addWidget(self._label)
        layout.addStretch()
        self._frame = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._timer.start(350)

    def stop(self) -> None:
        self._timer.stop()

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % len(self._FRAMES)
        self._label.setText(self._FRAMES[self._frame])
