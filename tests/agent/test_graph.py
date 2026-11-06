from langchain_core.messages import AIMessage, HumanMessage

from jarvis.agent.graph import screen_question


def test_screen_question_recognizes_explicit_desktop_requests():
    assert screen_question(HumanMessage("What is on my desktop?")) == "What is on my desktop?"
    question = "What do you see on my screen?"
    assert screen_question(HumanMessage(question)) == question
    assert screen_question(HumanMessage("Analyze both monitors")) == "Analyze both monitors"


def test_screen_question_leaves_other_requests_for_the_model():
    assert screen_question(HumanMessage("Open Paint")) is None
    assert screen_question(AIMessage("What is on my screen?")) is None
