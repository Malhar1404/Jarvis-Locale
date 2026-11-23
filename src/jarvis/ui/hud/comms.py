"""Comms: the chat panel's body - message bubbles plus the input row (text, mic, send).

Only the conversation lives here. What the agent *does* (tools, screenshots, timings) goes to
the Mind panel instead, so the chat stays readable.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from jarvis.ui.hud.commands import SLASH_COMMANDS
from jarvis.ui.hud.style import STYLESHEET


def make_scroll_column() -> tuple[QScrollArea, QVBoxLayout]:
    """A transparent scroll area holding a top-down column. Items are inserted above a trailing
    stretch, so they stack from the top. It auto-scrolls to the bottom whenever content grows -
    including a reply that is still streaming in - by listening to the scrollbar's range.
    """
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.viewport().setAutoFillBackground(False)
    content = QWidget(objectName="scrollContent")
    content.setAutoFillBackground(False)
    column = QVBoxLayout(content)
    column.setContentsMargins(14, 12, 14, 12)
    column.setSpacing(12)
    column.addStretch()
    scroll.setWidget(content)
    bar = scroll.verticalScrollBar()
    bar.rangeChanged.connect(lambda _lo, hi: bar.setValue(hi))
    return scroll, column


def _wrapping_label(text: str, object_name: str) -> QLabel:
    label = QLabel(text, objectName=object_name)
    label.setTextFormat(Qt.TextFormat.PlainText)  # never parsed as HTML, even with a "<" in it
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class ReplyBubble(QWidget):
    """Jarvis's reply, growing one streamed token at a time."""

    def __init__(self) -> None:
        super().__init__()
        self._text = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 24, 0)
        layout.setSpacing(3)
        layout.addWidget(QLabel("JARVIS", objectName="bubbleName"))
        self._body = _wrapping_label("", "bubbleJarvis")
        layout.addWidget(self._body)

    def append(self, text: str) -> None:
        self._text += text
        self._body.setText(self._text)


class CommsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        scroll, self._column = make_scroll_column()

        self.input_line = QLineEdit(objectName="commsInput")
        self.input_line.setPlaceholderText("Type, or hold MIC / F9 to talk")
        # A command only matches once what you've typed so far is itself a prefix of it (e.g.
        # "/", "/co"), so this never pops up for an ordinary message - only ever at the start of
        # typing a literal slash command. Selecting one just fills the box; Enter still sends it.
        completer = QCompleter(SLASH_COMMANDS, self.input_line)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        # The popup is its own top-level window - the HUD's stylesheet never reaches it unless
        # applied here directly (see the comment on QListView#commsCompleterPopup in style.py).
        completer.popup().setObjectName("commsCompleterPopup")
        completer.popup().setStyleSheet(STYLESHEET)
        self.input_line.setCompleter(completer)
        self.mic_button = QPushButton("MIC", objectName="commsMic")
        self.mic_button.setToolTip("Hold to talk (fills the box so you can check it first)")
        self.send_button = QPushButton("SEND", objectName="commsSend")
        for button in (self.mic_button, self.send_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(12, 10, 12, 12)
        input_row.setSpacing(8)
        input_row.addWidget(self.input_line, 1)
        input_row.addWidget(self.mic_button)
        input_row.addWidget(self.send_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(scroll, 1)
        layout.addLayout(input_row)

    def _add(self, widget: QWidget) -> None:
        self._column.insertWidget(self._column.count() - 1, widget)

    def add_user(self, text: str) -> None:
        bubble = _wrapping_label(text, "bubbleUser")
        bubble.setMaximumWidth(290)
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(40, 0, 0, 0)
        row_layout.addStretch()
        row_layout.addWidget(bubble)
        self._add(row)

    def start_reply(self) -> ReplyBubble:
        bubble = ReplyBubble()
        self._add(bubble)
        return bubble

    def add_note(self, text: str) -> None:
        label = _wrapping_label(text, "bubbleNote")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._add(label)

    def add_error(self, text: str) -> None:
        self._add(_wrapping_label(f"⚠ {text}", "bubbleError"))

    def set_busy(self, busy: bool) -> None:
        for widget in (self.input_line, self.mic_button, self.send_button):
            widget.setEnabled(not busy)
        if not busy:
            self.input_line.setFocus()

    def set_recording(self, recording: bool) -> None:
        self.mic_button.setText("REC" if recording else "MIC")
        self.mic_button.setProperty("recording", recording)
        # Qt only re-reads [recording="true"]-style selectors after an unpolish/polish.
        self.mic_button.style().unpolish(self.mic_button)
        self.mic_button.style().polish(self.mic_button)
