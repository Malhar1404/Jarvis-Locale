import pytest
from PySide6.QtWidgets import QApplication

from jarvis.ui.hud.comms import CommsView


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _completions(view: CommsView) -> list[str]:
    completer = view.input_line.completer()
    completer.setCompletionPrefix(view.input_line.text())
    model = completer.completionModel()
    return [model.data(model.index(i, 0)) for i in range(completer.completionCount())]


def test_typing_a_slash_shows_the_compact_command(app):
    view = CommsView()
    view.input_line.setText("/")
    assert "/compact" in _completions(view)


def test_typing_an_ordinary_message_shows_no_commands(app):
    view = CommsView()
    view.input_line.setText("open calculator")
    assert _completions(view) == []
