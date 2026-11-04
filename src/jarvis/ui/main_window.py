"""The main window. Knows nothing about LangGraph - only the AgentEvent stream, the same
contract cli.py already uses. The chat area is a Timeline of Cards (see cards.py) rather than
a single text box, so a tool call, a result, and an approval request can each be their own
widget - which is what lets an approval have real buttons and "thinking" actually animate.
"""

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from jarvis.agent.events import (
    AgentEvent,
    ApprovalRequest,
    Error,
    Thinking,
    Token,
    ToolCall,
    ToolResult,
)
from jarvis.agent.runner import Agent
from jarvis.config import MODEL
from jarvis.ui import theme
from jarvis.ui.cards import (
    ApprovalCard,
    AssistantCard,
    ErrorCard,
    ThinkingIndicator,
    ToolCallCard,
    ToolResultCard,
    UserCard,
)
from jarvis.ui.timeline import Timeline
from jarvis.ui.tray import Tray, make_icon
from jarvis.ui.worker import AgentWorker


def _glow(widget: QWidget, color: str = theme.ACCENT, radius: int = 24) -> None:
    """A soft colored glow around a widget's edges. Works because the widget is fully opaque:
    the shadow effect blurs the widget's alpha silhouette, so it only shows up at the border.
    """
    effect = QGraphicsDropShadowEffect(widget)
    effect.setColor(QColor(color))
    effect.setBlurRadius(radius)
    effect.setOffset(0, 0)
    widget.setGraphicsEffect(effect)


class MainWindow(QMainWindow):
    # Crossing from this (main) thread into the worker's thread must go through signals - Qt
    # then queues the call onto the worker's thread instead of running it here by mistake.
    send_requested = Signal(str)
    resume_requested = Signal(str)

    def __init__(self, agent: Agent) -> None:
        super().__init__()
        self.setWindowTitle("Jarvis")
        self.setStyleSheet(theme.STYLESHEET)
        self.setWindowIcon(make_icon())
        self._quitting = False

        self.title_label = QLabel("J A R V I S")
        self.title_label.setObjectName("title")
        title_font = self.title_label.font()
        title_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 150)
        self.title_label.setFont(title_font)

        header_row = QHBoxLayout()
        header_row.addWidget(self.title_label)
        header_row.addStretch()

        self.timeline = Timeline()
        _glow(self.timeline)
        self._thinking_card: ThinkingIndicator | None = None
        self._current_reply: AssistantCard | None = None

        self.input_line = QLineEdit(placeholderText="Ask Jarvis...", objectName="inputLine")
        _glow(self.input_line, radius=16)
        self.send_button = QPushButton("Send", objectName="sendButton")

        input_row = QHBoxLayout()
        input_row.addWidget(self.input_line)
        input_row.addWidget(self.send_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(12)
        layout.addLayout(header_row)
        layout.addWidget(self.timeline)
        layout.addLayout(input_row)
        central = QWidget(objectName="central")
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.send_button.clicked.connect(self._on_send)
        self.input_line.returnPressed.connect(self._on_send)

        self.status_label = QLabel("IDLE")
        self.model_label = QLabel(MODEL)
        self.statusBar().addWidget(self.status_label)
        self.statusBar().addPermanentWidget(self.model_label)

        self.tray: Tray | None = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = Tray(self)
            self.tray.show()

        self._thread = QThread()
        self._worker = AgentWorker(agent)
        self._worker.moveToThread(self._thread)
        self._worker.event.connect(self._on_event)
        self._worker.turn_done.connect(self._on_turn_done)
        self.send_requested.connect(self._worker.send)
        self.resume_requested.connect(self._worker.resume)
        self._thread.start()

    def _on_send(self) -> None:
        text = self.input_line.text().strip()
        if not text:
            return
        self.input_line.clear()
        self.timeline.add(UserCard(text))
        self._current_reply = None
        self._show_thinking()
        self._set_busy(True)
        self._set_status("THINKING...")
        self.send_requested.emit(text)

    def _on_event(self, event: AgentEvent) -> None:
        match event:
            case Thinking():
                pass  # we already show the thinking indicator as soon as we send/resume
            case Token(text=text):
                self._hide_thinking()
                if self._current_reply is None:
                    self._current_reply = AssistantCard()
                    self.timeline.add(self._current_reply)
                self._current_reply.append_token(text)
            case ToolCall(name=name, args=args):
                self._hide_thinking()
                self._current_reply = None
                self._set_status(f"RUNNING: {name}")
                self.timeline.add(ToolCallCard(name, args))
            case ToolResult(name=name, content=content, status=status):
                self._hide_thinking()
                self.timeline.add(ToolResultCard(name, content, status))
            case Error(message=message):
                self._hide_thinking()
                self._current_reply = None
                self.timeline.add(ErrorCard(message))
            case ApprovalRequest(name=name, args=args, tier=tier):
                self._hide_thinking()
                self._current_reply = None
                self._set_status("AWAITING APPROVAL")
                card = ApprovalCard(name, args, tier)
                card.decided.connect(self._on_approval_decided)
                self.timeline.add(card)

    def _on_approval_decided(self, decision: str) -> None:
        self._set_status("THINKING...")
        self._show_thinking()
        self.resume_requested.emit(decision)

    def _on_turn_done(self) -> None:
        self._hide_thinking()
        self._current_reply = None
        self._set_busy(False)
        self._set_status("IDLE")

    def _show_thinking(self) -> None:
        if self._thinking_card is None:
            self._thinking_card = ThinkingIndicator()
            self._thinking_card.start()
            self.timeline.add(self._thinking_card)

    def _hide_thinking(self) -> None:
        if self._thinking_card is not None:
            card = self._thinking_card
            self._thinking_card = None
            card.stop()
            self.timeline.remove(card)

    def _set_busy(self, busy: bool) -> None:
        self.input_line.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        if not busy:
            self.input_line.setFocus()

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def quit_app(self) -> None:
        self._quitting = True
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:
        if self.tray is not None and not self._quitting:
            event.ignore()
            self.hide()
            self.tray.sync_toggle_text()
            self.tray.showMessage(
                "Jarvis",
                "Still running in the tray - right-click the icon to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
            return
        self._thread.quit()
        self._thread.wait()
        super().closeEvent(event)
