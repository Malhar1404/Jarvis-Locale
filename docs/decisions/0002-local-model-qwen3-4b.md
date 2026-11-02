# 0002: Local model qwen3:4b-instruct via Ollama

**Decision:** use `qwen3:4b-instruct` (non-thinking). `llama3.2:3b` is the fallback.

**Why:**
- The GPU has 4 GB VRAM, so 8B models would spill to CPU and be slow. qwen3 supports tool calling.
- The plain `qwen3:4b` tag is the **thinking-only** variant (same file as `4b-thinking`). It always
  writes long thoughts, `reasoning=False` is ignored, and a voice assistant would read the thoughts
  aloud. Found in Phase 1 step 5. The instruct variant answers directly.

**Trade-off:** small models are less reliable with many tools and with classification (seen in
Phase 1 step 4), so keep the tool list short with clear descriptions. A thinking model may be
added later as a "think harder" mode, with its thoughts shown in the UI activity panel.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| `qwen3:4b-thinking` (a.k.a. `qwen3:4b`) | Hard problems, a visible "thinking" panel | Slow; thoughts leak into replies; bad for voice |
| `llama3.2:3b` | Lighter, fast | Fallback; weaker at tool calling |
| `phi4-mini`, `gemma3:4b` | Similar size, different strengths | Worth comparing later in the eval (Phase 9) |
| 8B models (`qwen3:8b`, `llama3.1:8b`) | Better reasoning and tool use | Do not fit in 4 GB VRAM; slow on CPU |
| Cloud models (Claude, GPT) | Best quality | Not private or local, which is the project goal |
| LM Studio / llama.cpp instead of Ollama | More tuning control | Ollama is simpler on Windows |
