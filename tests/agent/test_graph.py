from langchain_core.messages import AIMessage, HumanMessage

from jarvis.agent.graph import has_tool_calls, screen_question


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
