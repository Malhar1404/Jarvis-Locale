from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from jarvis.agent.runner import _with_current_system_prompt


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
