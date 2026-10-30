# 0002: Local model qwen3:4b via Ollama

**Decision:** start with `qwen3:4b`; `llama3.2:3b` is the fallback.

**Why:** the GPU has 4 GB VRAM, so 8B models would spill to CPU and be slow. qwen3 supports tool calling.

**Trade-off:** small models are less reliable with many tools, so keep the tool list short with
clear descriptions. Revisit if the hardware changes.
