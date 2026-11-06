from jarvis.cli import run
from jarvis.setup import SYSTEM_PROMPT, build_tools


def test_system_prompt_mentions_jarvis():
    assert "Jarvis" in SYSTEM_PROMPT


def test_run_is_importable_without_calling_it():
    # run() blocks on input() - we only check it exists and is callable, never invoke it here.
    assert callable(run)


def test_screen_inspection_is_registered_with_the_agent():
    assert "inspect_screen" in {tool.name for tool in build_tools()}
