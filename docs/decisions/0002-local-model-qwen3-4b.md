# 0002: Local model qwen3:4b via Ollama

**Decision:** start with `qwen3:4b`; `llama3.2:3b` is the fallback.

**Why:** the GPU has 4 GB VRAM, so 8B models would spill to CPU and be slow. qwen3 supports tool calling.

**Trade-off:** small models are less reliable with many tools, so keep the tool list short with
clear descriptions. Revisit if the hardware changes.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| `llama3.2:3b` | Lighter, fast | Fallback; weaker at tool calling |
| `phi4-mini`, `gemma3:4b` | Similar size, different strengths | Worth comparing later in the eval (Phase 9) |
| 8B models (`qwen3:8b`, `llama3.1:8b`) | Better reasoning and tool use | Do not fit in 4 GB VRAM; slow on CPU |
| Cloud models (Claude, GPT) | Best quality | Not private or local, which is the project goal |
| LM Studio / llama.cpp instead of Ollama | More tuning control | Ollama is simpler on Windows |
