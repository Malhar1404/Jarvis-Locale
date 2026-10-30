# Jarvis

A local voice assistant for Windows, built step by step to learn LangChain, LangGraph and agent design.

- Runs fully local with [Ollama](https://ollama.com) (`qwen3:4b`).
- Asks for permission before anything risky.
- Desktop UI (PySide6) shows what the agent is thinking and doing.

## Setup
```
uv sync
ollama pull qwen3:4b
uv run python examples/phase0_hello_llm.py
```

## Docs
Open the `docs/` folder as an [Obsidian](https://obsidian.md) vault. Start with
[docs/STATUS.md](docs/STATUS.md) (where we are) and [docs/PLAN.md](docs/PLAN.md) (the roadmap).
