# Structured output

**One line:** make the model fill a fixed "form" (a Pydantic class) so our code gets clean data instead of free text.

## Why it exists
Jarvis must turn "remind me to call mom tomorrow at 5" into fields it can use: task, when, urgent.
Parsing free text by hand breaks easily.

## How it works
```python
class Reminder(BaseModel):
    task: str = Field(description="What to be reminded about")
    when: str = Field(description="When, in the user's words")
    urgent: bool = Field(description="True only if the user says it is urgent")

result = llm.with_structured_output(Reminder).invoke("Remind me to call mom tomorrow at 5pm")
result.task   # 'call mom'
```
- The `Field` descriptions are shown to the model, like a tool docstring. Write them clearly.
- `Literal["a", "b"]` limits the answer to a fixed set. Useful for routing requests.
- **Tool call vs structured output:** a tool call asks us to *do* something; structured output *extracts data*.
- Observed with `qwen3:4b`: extraction worked well; intent classification was mostly wrong
  because the choices had no definitions. Test small models on real cases.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Ask for JSON in the prompt, `json.loads` | Any model | Breaks when the model adds extra words |
| Ollama `format` JSON schema | Same thing underneath | `with_structured_output` calls it for us |
| `instructor` / `outlines` | Retries, strict constrained decoding | Extra dependency |
| Regex / keyword rules | Very simple fixed commands | Cannot handle natural phrasing |

## Related
- [[tool-calling]]
- [[prompt-templates]]
