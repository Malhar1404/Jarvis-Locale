# Phase 0: Foundations

**Status:** done
**Date:** 2026-10-30

## Goal
Get a working environment and make the first call to a local model through LangChain.

## What we built
- uv project on Python 3.12 with `langchain`, `langchain-ollama`, `langgraph`.
- Ollama installed with `qwen3:4b` pulled.
- `examples/phase0_hello_llm.py`: calls the model with `invoke` and with `stream`.

## Concepts learned
- [[chat-model]]
- [[messages]]
- [[streaming]]

## How it works (my own words)
_Write this yourself: what happens between `llm.invoke(messages)` and the answer printing?_

## What confused me / questions I still have
- 

## Code to look at
- `examples/phase0_hello_llm.py`

## Decisions made
- [[0001-pyside6-desktop-ui]]
- [[0002-local-model-qwen3-4b]]
