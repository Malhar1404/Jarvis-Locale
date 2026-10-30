from jarvis.tools.basic import get_time, multiply


def test_multiply():
    assert multiply.invoke({"a": 123456, "b": 654321}) == 123456 * 654321


def test_get_time_returns_text():
    assert isinstance(get_time.invoke({}), str)


def test_tool_description_comes_from_docstring():
    assert "Multiply" in multiply.description
