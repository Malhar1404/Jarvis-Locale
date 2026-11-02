import pytest

from jarvis.tools.basic import divide, get_system_info, multiply
from jarvis.tools.runner import run_tool

TOOLS = {t.name: t for t in (divide, multiply, get_system_info)}


def call(name, args, call_id="id-1"):
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def test_success_returns_result_with_same_id():
    msg = run_tool(call("multiply", {"a": 6, "b": 7}, "abc"), TOOLS)
    assert msg.content == "42"
    assert msg.tool_call_id == "abc"
    assert msg.status == "success"


def test_exception_inside_tool_becomes_error_message():
    msg = run_tool(call("divide", {"a": 1, "b": 0}), TOOLS)
    assert msg.status == "error"
    assert "ZeroDivisionError" in msg.content


def test_unknown_tool_lists_available_tools():
    msg = run_tool(call("open_rocket", {}), TOOLS)
    assert msg.status == "error"
    assert "multiply" in msg.content


def test_bad_arguments_become_error_message():
    msg = run_tool(call("multiply", {"a": "not a number"}), TOOLS)
    assert msg.status == "error"


@pytest.mark.parametrize("word", ["CPU", "Memory", "Disk", "Battery"])
def test_system_info_has_all_sections(word):
    assert word in get_system_info.invoke({})
