"""Runs the Agent on its own thread so the Qt event loop (and the window) never freezes while
the model is thinking. The main thread never calls this object's methods directly - it only
connects signals to these slots, so Qt marshals the call onto the worker's thread for us.
"""

from collections.abc import Iterator

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from jarvis.agent.events import AgentEvent, ApprovalRequest, Token
from jarvis.agent.runner import Agent
from jarvis.voice.stt import transcribe
from jarvis.voice.tts import SentenceSpeaker


class AgentWorker(QObject):
    event = Signal(object)  # emits one AgentEvent at a time
    turn_done = Signal()  # the agent is idle again, waiting for the next message
    transcribed = Signal(str)  # a recorded clip has been turned into text

    def __init__(self, agent: Agent) -> None:
        super().__init__()
        self._agent = agent
        # Whether the reply to the turn in progress should be spoken - set by send(), and still
        # in effect through any resume() calls that finish the same turn after an approval.
        self._speak_current_turn = False

    @Slot(str, bool)
    def send(self, text: str, speak: bool) -> None:
        self._speak_current_turn = speak
        self._drive(self._agent.run(text))

    @Slot(str)
    def resume(self, decision: str) -> None:
        self._drive(self._agent.resume(decision))

    @Slot(object)
    def transcribe(self, audio: np.ndarray) -> None:
        """Runs faster-whisper on the worker thread (it's CPU-bound and not instant) so the
        window doesn't freeze while a recording is turned into text.
        """
        self.transcribed.emit(transcribe(audio))

    def _drive(self, events: Iterator[AgentEvent]) -> None:
        speaker = SentenceSpeaker() if self._speak_current_turn else None
        paused = False
        for ev in events:
            if speaker is not None and isinstance(ev, Token):
                speaker.feed(ev.text)
            paused = isinstance(ev, ApprovalRequest)
            if paused and speaker is not None:
                speaker.flush()  # say whatever Jarvis announced before pausing for approval
            self.event.emit(ev)
        if not paused:
            if speaker is not None:
                speaker.flush()
            self.turn_done.emit()
