"""Remember and recall small facts about the user (name, usual folders, preferences) that should
survive across conversations - not just within one chat, like the checkpointed history already does.

remember_fact is ASK_ONCE: same reasoning as write_file - it creates or silently overwrites
persistent content, a real lasting change, even though (like write_file) it can't touch anything
outside Jarvis's own local storage. recall_fact/list_remembered_facts are AUTO, like the read-only
file tools - reading back what was already approved to remember needs no further confirmation.
"""

from langchain_core.tools import tool

from jarvis.memory.store import recall, recall_all, remember
from jarvis.safety.tiers import RiskTier, risk_tier


@risk_tier(RiskTier.ASK_ONCE)
@tool
def remember_fact(key: str, value: str) -> str:
    """Remember a fact about the user for future conversations.

    E.g. key="name", value="Jatin", or key="project_folder", value="C:/dev/jarvis". Overwrites
    any existing fact already remembered under the same key.
    """
    remember(key, value)
    return f"Remembered: {key} = {value}."


@risk_tier(RiskTier.AUTO)
@tool
def recall_fact(key: str) -> str:
    """Recall a single previously remembered fact about the user by its key."""
    value = recall(key)
    return value if value is not None else f"Nothing remembered for '{key}'."


@risk_tier(RiskTier.AUTO)
@tool
def list_remembered_facts() -> str:
    """List every fact remembered about the user so far."""
    facts = recall_all()
    if not facts:
        return "(nothing remembered yet)"
    return "\n".join(f"{key}: {value}" for key, value in facts.items())
