from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

import jarvis.agent.runner as runner
from jarvis.agent.runner import _old_messages, _transcript_line, _with_current_system_prompt


def test_current_system_prompt_replaces_persisted_one_in_place():
    old_system = SystemMessage("Old instructions", id="system-id")
    messages = [old_system, HumanMessage("Hello", id="human-id"), AIMessage("Hi", id="ai-id")]

    updated = _with_current_system_prompt(messages, "New instructions")

    assert [message.id for message in updated] == ["system-id", "human-id", "ai-id"]
    assert updated[0].content == "New instructions"


def test_current_system_prompt_is_added_when_a_legacy_checkpoint_has_none():
    messages = [HumanMessage("Hello", id="human-id")]

    updated = _with_current_system_prompt(messages, "New instructions")

    assert isinstance(updated[0], SystemMessage)
    assert updated[0].content == "New instructions"
    assert updated[1:] == messages


def test_old_messages_is_empty_for_a_short_conversation():
    messages = [SystemMessage("be nice"), HumanMessage("hi"), AIMessage("hello")]
    assert _old_messages(messages) == []


def test_old_messages_returns_the_droppable_tail(monkeypatch):
    # Real history always has real ids by the time it reaches here - LangGraph's add_messages
    # reducer assigns them (checked directly) - so these synthetic messages need ids too, or
    # every id-less message compares equal and nothing ever counts as "old".
    monkeypatch.setattr(runner, "HISTORY_TRIM_TOKENS", 600)  # // 2 = 300, same budget as before
    system = SystemMessage("be nice", id="s")
    messages = [system]
    for i in range(20):
        messages.append(HumanMessage(f"question number {i} " * 10, id=f"h{i}"))
        messages.append(AIMessage(f"answer number {i} " * 10, id=f"a{i}"))

    old = _old_messages(messages)

    assert old
    assert system not in old
    assert messages[-1] not in old  # the most recent turn is always kept, never "old"


def test_transcript_line_formats_human_and_ai_turns():
    assert _transcript_line(HumanMessage("hi")) == "User: hi"
    assert _transcript_line(AIMessage("hello")) == "Jarvis: hello"


def test_transcript_line_skips_empty_or_tool_call_only_messages():
    assert _transcript_line(AIMessage("")) == ""
    empty_tool_call = AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "1"}])
    assert _transcript_line(empty_tool_call) == ""
