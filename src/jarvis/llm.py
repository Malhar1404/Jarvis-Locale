"""One place that builds the chat model, so every part of Jarvis configures it the same way."""

from langchain_ollama import ChatOllama

from jarvis import config


def make_llm(*, reasoning: bool | None = None) -> ChatOllama:
    """Build the local chat model. `reasoning` overrides the JARVIS_REASONING setting."""
    return ChatOllama(
        model=config.MODEL,
        temperature=0,
        reasoning=config.REASONING if reasoning is None else reasoning,
    )
