# Risk tiers

**One line:** every tool declares, right above its definition, how much it is trusted to run on its own.

## Why it exists
`CLAUDE.md`: "Permissions are enforced in Python (`safety/`), never only in the prompt." A tool's
docstring can ask the model to "always confirm before deleting" - the model can ignore that. A
Python `if` statement cannot be talked out of running.

## How it works
```python
@risk_tier(RiskTier.ASK_ONCE)
@tool
def open_app(name: str) -> str:
    """Pretend to open an application by name."""
    return f"opened {name}"
```
`@tool` runs first (bottom-up) and turns the function into a `BaseTool`. `@risk_tier(...)` then
sets `tool.metadata = {"risk_tier": "ask_once"}` - reusing a field `BaseTool` already has, instead
of inventing new plumbing. `get_risk_tier(tool)` reads it back, and defaults to `ALWAYS_ASK` if a
tool never declared one at all - **fail safe, not fail open**: forgetting to tag a tool makes it
*more* cautious, never less.

| Tier | Meaning |
|---|---|
| `auto` | Runs immediately, no question |
| `ask_once` | Ask the first time per conversation, then remember "yes" |
| `always_ask` | Ask every single time, no exceptions |
| `never` | The agent must never run this tool |

See [[interrupt-and-resume]] for how `ask_once`/`always_ask` actually pause the agent.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| `BaseTool.metadata` + decorator (this) | Declaration sits next to the tool; reuses an existing field | — |
| A separate `{tool_name: tier}` dict elsewhere | One place to read the whole list | Lives far from the tool; easy to add a tool and forget to update it |
| Subclass `BaseTool` per tier | Type-checker enforces it | Far more ceremony than this project needs |
| Naming convention (`risky_delete_file`) | Zero code | Nothing enforces it in Python - exactly what `CLAUDE.md` rules out |

## Related
- [[interrupt-and-resume]]
- [[tool-calling]]
