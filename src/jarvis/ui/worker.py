"""Runs the Agent on its own thread so the Qt event loop (and the window) never freezes while
the model is thinking. The main thread never calls this object's methods directly - it only
connects signals to these slots, so Qt marshals the call onto the worker's thread for us.
"""

from collections.abc import Iterator

from PySide6.QtCore import QObject, Signal, Slot

from jarvis.agent.events import AgentEvent, ApprovalRequest
from jarvis.agent.runner import Agent


class AgentWorker(QObject):
    event = Signal(object)  # emits one AgentEvent at a time
    turn_done = Signal()  # the agent is idle again, waiting for the next message

    def __init__(self, agent: Agent) -> None:
        super().__init__()
        self._agent = agent

    @Slot(str)
    def send(self, text: str) -> None:
        self._drive(self._agent.run(text))

    @Slot(str)
    def resume(self, decision: str) -> None:
        self._drive(self._agent.resume(decision))

    def _drive(self, events: Iterator[AgentEvent]) -> None:
        paused = False
        for ev in events:
            paused = isinstance(ev, ApprovalRequest)
            self.event.emit(ev)
        if not paused:
            self.turn_done.emit()
