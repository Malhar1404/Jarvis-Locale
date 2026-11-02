"""Phase 1, step 4: structured output. Turn messy text into clean data with a Pydantic class.

Run with:  uv run python examples/phase1_step4_structured_output.py
"""

from typing import Literal

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from jarvis import config

llm = ChatOllama(model=config.MODEL, temperature=0)


# 1) Describe the "form" the model must fill. The Field descriptions are shown to the model,
#    just like a tool's docstring, so write them clearly.
class Reminder(BaseModel):
    task: str = Field(description="What the user wants to be reminded about")
    when: str = Field(description="When, in the user's own words, for example 'tomorrow at 5pm'")
    urgent: bool = Field(description="True only if the user says it is urgent or important")


reminder_llm = llm.with_structured_output(Reminder)

for text in [
    "Remind me to call mom tomorrow at 5pm",
    "Please remind me to pay the electricity bill on Friday, it's really urgent!",
]:
    result = reminder_llm.invoke(text)
    print(f"INPUT:  {text}")
    print(f"  type:   {type(result).__name__}")  # a real Reminder object, not text
    print(f"  task={result.task!r}  when={result.when!r}  urgent={result.urgent}\n")


# 2) Classification: Literal limits the answer to a fixed set of choices.
#    Jarvis can use this to decide what kind of request it received.
class Intent(BaseModel):
    kind: Literal["set_reminder", "open_app", "system_question", "chat"] = Field(
        description="The type of request the user made"
    )


intent_llm = llm.with_structured_output(Intent)

for text in [
    "Open Spotify",
    "How much battery do I have left?",
    "Remind me to drink water in an hour",
    "Tell me about black holes",
]:
    print(f"{text!r:42} -> {intent_llm.invoke(text).kind}")
