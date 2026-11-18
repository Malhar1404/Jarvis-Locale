from jarvis.voice.tts import strip_for_speech


def test_strip_for_speech_removes_markdown():
    text = "**Done.** Here's `code` and _notes_."
    assert strip_for_speech(text) == "Done. Here's code and notes."


def test_strip_for_speech_removes_heading_and_bullet_markers():
    assert strip_for_speech("# Title\n- one\n- two") == "Title\none\ntwo"


def test_strip_for_speech_removes_emoji():
    assert strip_for_speech("All set! \U0001f680") == "All set!"


def test_strip_for_speech_leaves_plain_text_alone():
    assert strip_for_speech("Brightness is now 50 percent.") == "Brightness is now 50 percent."
