from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

import jarvis.agent.graph as graph
from jarvis.agent.graph import has_tool_calls, screen_question, trim_history


def test_screen_question_recognizes_explicit_desktop_requests():
    assert screen_question(HumanMessage("What is on my desktop?")) == "What is on my desktop?"
    question = "What do you see on my screen?"
    assert screen_question(HumanMessage(question)) == question
    assert screen_question(HumanMessage("Analyze both monitors")) == "Analyze both monitors"


def test_screen_question_leaves_other_requests_for_the_model():
    assert screen_question(HumanMessage("Open Paint")) is None
    assert screen_question(AIMessage("What is on my screen?")) is None


def test_has_tool_calls_handles_human_and_ai_messages():
    assert not has_tool_calls(HumanMessage("Open Calculator"))
    assert has_tool_calls(
        AIMessage(content="", tool_calls=[{"name": "open_app", "args": {}, "id": "call-1"}])
    )


def test_trim_history_is_a_noop_under_budget():
    messages = [SystemMessage("be nice"), HumanMessage("hi"), AIMessage("hello")]
    assert trim_history(messages) == messages


def test_trim_history_keeps_system_message_and_drops_oldest_turns(monkeypatch):
    monkeypatch.setattr(graph, "HISTORY_TRIM_TOKENS", 300)
    system = SystemMessage("be nice")
    messages = [system]
    for i in range(20):
        messages.append(HumanMessage(f"question number {i} " * 10))
        messages.append(AIMessage(f"answer number {i} " * 10))

    trimmed = trim_history(messages)

    assert trimmed[0] is system
    assert trimmed[-1] == messages[-1]
    assert len(trimmed) < len(messages)
