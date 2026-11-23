import pytest

from jarvis.ui.hud.commands import compact_command, interactive_mode_command


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Interactive mode on", True),
        ("Jarvis, turn on interactive mode", True),
        ("switch to gesture mode", True),
        ("turn off interactive mode", False),
        ("exit interactive mode", False),
        ("what is interactive mode?", None),
        ("turn on the lights", None),
    ],
)
def test_interactive_mode_command(text, expected):
    assert interactive_mode_command(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/compact", True),
        ("/COMPACT", True),
        ("  /compact  ", True),
        ("please compact the conversation", False),
        ("/compactness", False),
    ],
)
def test_compact_command(text, expected):
    assert compact_command(text) is expected
