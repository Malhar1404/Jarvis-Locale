# Reasoning (thinking) models

**One line:** some models write long private thoughts before answering. Good for hard problems, bad for fast voice replies.

## Why it matters here
A voice assistant must answer quickly and must never read its thoughts aloud.

## How it works
- Ollama marks such models with a `thinking` capability. `ollama show <model>` lists it.
- In `langchain-ollama`, `reasoning=True` moves the thoughts into `AIMessage.additional_kwargs["reasoning_content"]`
  and keeps `content` clean. `reasoning=False` turns thinking off. `None` uses the model default and
  leaves `<think>` text inside `content`.
- **Catch:** thinking-only variants (`qwen3:4b` = `qwen3:4b-thinking`) ignore `reasoning=False` and
  always think. Use the `-instruct` variant for no thinking.
- Idea for the UI (Phase 6): a "think harder" mode that shows `reasoning_content` in the activity panel.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Instruct model, no thinking (our choice) | Fast, direct, safe to speak | Weaker on hard multi-step problems |
| Thinking model + `reasoning=True` | Hard tasks, visible thinking | Slow on a 4 GB GPU |
| Strip `<think>` with a regex | Quick fix on any model | Fragile, and you still pay the thinking time |

## Related
- [[chat-model]]
- [[0002-local-model-qwen3-4b]]
