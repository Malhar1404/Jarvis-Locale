"""The main window. Knows nothing about LangGraph - only the AgentEvent stream, the same
contract cli.py already uses. The chat area is a Timeline of Cards (see cards.py) rather than
a single text box, so a tool call, a result, and an approval request can each be their own
widget - which is what lets an approval have real buttons and "thinking" actually animate.
"""

from PySide6.QtCore import Qt, QThread, Signal
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
from jarvis.config import MODEL, PUSH_TO_TALK_KEY
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
from jarvis.ui.orb import Orb
from jarvis.ui.timeline import Timeline
from jarvis.ui.tools_panel import ToolsPanel
from jarvis.ui.tray import Tray, make_icon
from jarvis.ui.worker import AgentWorker
from jarvis.vision.hand_state import HandState
from jarvis.vision.hand_tracking import HandTracker
from jarvis.voice.audio_level import AudioLevel
from jarvis.voice.hotkey import Recorder, listen_push_to_talk


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
    send_requested = Signal(str, bool)  # text, speak_the_reply
    resume_requested = Signal(str)
    transcribe_requested = Signal(object)  # a recorded numpy clip
    hotkey_pressed = Signal()  # pynput calls these from its own thread, not the GUI thread
    hotkey_released = Signal()

    def __init__(self, agent: Agent, tool_names: list[str]) -> None:
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
        self.mic_button = QPushButton("\U0001f3a4", objectName="micButton")
        self.mic_button.setToolTip("Hold to talk")
        self.send_button = QPushButton("Send", objectName="sendButton")

        input_row = QHBoxLayout()
        input_row.addWidget(self.mic_button)
        input_row.addWidget(self.input_line)
        input_row.addWidget(self.send_button)

        self._level = AudioLevel()  # drives the orb - only fed by Jarvis's own TTS, not your mic
        self._recorder = Recorder()
        self._recording = False
        self._busy = False
        self._voice_auto_send = False  # set just before a release, read when transcription lands
        self._voice_turn = False  # True if the text about to be sent came from voice input

        chat_layout = QVBoxLayout()
        chat_layout.setSpacing(12)
        chat_layout.addLayout(header_row)
        chat_layout.addWidget(self.timeline)
        chat_layout.addLayout(input_row)
        self.chat_column = QWidget(objectName="chatColumn")
        self.chat_column.setLayout(chat_layout)

        self.tools_panel = ToolsPanel(tool_names)
        self._hand_state = HandState()
        self._hand_tracker = HandTracker(self._hand_state)
        self.orb = Orb(level_source=self._level, hand_source=self._hand_state)
        self.orb.setToolTip("Click to expand")
        self.orb.clicked.connect(self._toggle_orb_fullscreen)
        _glow(self.orb, radius=18)
        self._orb_fullscreen = False

        self.camera_indicator = QLabel("● CAMERA ACTIVE - move your hand to control the orb")
        self.camera_indicator.setObjectName("cameraIndicator")
        self.camera_indicator.hide()

        side_layout = QVBoxLayout()
        side_layout.setSpacing(16)
        side_layout.addWidget(self.tools_panel)
        side_layout.addWidget(self.camera_indicator)
        side_layout.addWidget(self.orb)
        self.side_column = QWidget(objectName="sideColumn")
        self.side_column.setLayout(side_layout)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(24, 18, 24, 18)
        self.body_layout.setSpacing(16)
        self.body_layout.addWidget(self.chat_column, 1)
        self.body_layout.addWidget(self.side_column)
        central = QWidget(objectName="central")
        central.setLayout(self.body_layout)
        self.setCentralWidget(central)

        self.send_button.clicked.connect(self._on_send)
        self.input_line.returnPressed.connect(self._on_send)
        self.mic_button.pressed.connect(self._on_mic_press)
        self.mic_button.released.connect(self._on_mic_release)
        self.hotkey_pressed.connect(self._on_hotkey_pressed)
        self.hotkey_released.connect(self._on_hotkey_released)

        # listen_push_to_talk's callbacks run on pynput's own thread, never the GUI thread - they
        # may only ever emit a signal (thread-safe from anywhere), never touch a widget directly.
        self._hotkey_listener = listen_push_to_talk(
            PUSH_TO_TALK_KEY, self.hotkey_pressed.emit, self.hotkey_released.emit
        )

        self.status_label = QLabel("IDLE")
        self.model_label = QLabel(MODEL)
        self.statusBar().addWidget(self.status_label)
        self.statusBar().addPermanentWidget(self.model_label)

        self.tray: Tray | None = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = Tray(self)
            self.tray.show()

        self._thread = QThread()
        self._worker = AgentWorker(agent, level=self._level)
        self._worker.moveToThread(self._thread)
        self._worker.event.connect(self._on_event)
        self._worker.turn_done.connect(self._on_turn_done)
        self._worker.transcribed.connect(self._on_transcribed)
        self.send_requested.connect(self._worker.send)
        self.resume_requested.connect(self._worker.resume)
        self.transcribe_requested.connect(self._worker.transcribe)
        self._thread.start()

    def _on_send(self) -> None:
        text = self.input_line.text().strip()
        if not text:
            return
        speak = self._voice_turn
        self._voice_turn = False
        self.input_line.clear()
        self.timeline.add(UserCard(text))
        self._current_reply = None
        self._show_thinking()
        self._set_busy(True)
        self._set_status("THINKING...")
        self.send_requested.emit(text, speak)

    def _on_mic_press(self) -> None:
        self._start_recording()

    def _on_mic_release(self) -> None:
        self._stop_recording(auto_send=False)

    def _on_hotkey_pressed(self) -> None:
        self._start_recording()

    def _on_hotkey_released(self) -> None:
        self._stop_recording(auto_send=True)

    def _start_recording(self) -> None:
        # The global hotkey isn't a widget, so it isn't disabled by _set_busy()'s
        # mic_button.setEnabled(False) the way a mouse click already is - check explicitly.
        if self._recording or self._busy:
            return
        self._recording = True
        self.mic_button.setProperty("recording", True)
        self._repolish(self.mic_button)
        self._set_status("LISTENING...")
        self._recorder.start()

    def _stop_recording(self, *, auto_send: bool) -> None:
        if not self._recording:
            return
        self._recording = False
        self._voice_auto_send = auto_send
        self.mic_button.setProperty("recording", False)
        self._repolish(self.mic_button)
        self._set_status("TRANSCRIBING...")
        audio = self._recorder.stop()
        self.transcribe_requested.emit(audio)

    def _on_transcribed(self, text: str) -> None:
        auto_send = self._voice_auto_send
        self._voice_auto_send = False
        self._set_status("IDLE")
        if not text:
            return
        self.input_line.setText(text)
        self._voice_turn = True
        if auto_send:
            self._on_send()
        else:
            self.input_line.setFocus()

    def _toggle_orb_fullscreen(self) -> None:
        self._orb_fullscreen = not self._orb_fullscreen
        self.chat_column.setVisible(not self._orb_fullscreen)
        self.tools_panel.setVisible(not self._orb_fullscreen)
        # Without a stretch factor, a layout sizes a widget to its own content once its only
        # sibling (chat_column) is hidden - this is what actually lets the orb fill the window.
        self.body_layout.setStretchFactor(self.side_column, 1 if self._orb_fullscreen else 0)

        # The webcam is privacy-sensitive, so it only ever runs while the orb is expanded, and
        # camera_indicator makes that visible rather than leaving it silently running.
        if self._orb_fullscreen:
            self._hand_tracker.start()
            self.camera_indicator.show()
        else:
            self._hand_tracker.stop()
            self.camera_indicator.hide()

    def keyPressEvent(self, event) -> None:
        if self._orb_fullscreen and event.key() == Qt.Key.Key_Escape:
            self._toggle_orb_fullscreen()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        """Qt only re-reads a stylesheet's dynamic-property selectors (like [recording="true"])
        after this - a plain setProperty() alone doesn't repaint anything.
        """
        widget.style().unpolish(widget)
        widget.style().polish(widget)

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
                self.tools_panel.set_active(name)
                self.timeline.add(ToolCallCard(name, args))
            case ToolResult(name=name, content=content, status=status):
                self._hide_thinking()
                self.tools_panel.set_active(None)
                self.timeline.add(ToolResultCard(name, content, status))
            case Error(message=message):
                self._hide_thinking()
                self._current_reply = None
                self.tools_panel.set_active(None)
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
        self.tools_panel.set_active(None)
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
        self._busy = busy
        self.input_line.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        self.mic_button.setEnabled(not busy)
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
        self._hotkey_listener.stop()
        self._hand_tracker.stop()
        self._thread.quit()
        self._thread.wait()
        super().closeEvent(event)
