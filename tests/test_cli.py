from jarvis.cli import SYSTEM_PROMPT, run


def test_system_prompt_mentions_jarvis():
    assert "Jarvis" in SYSTEM_PROMPT


def test_run_is_importable_without_calling_it():
    # run() blocks on input() - we only check it exists and is callable, never invoke it here.
    assert callable(run)
