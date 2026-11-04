# Audit log

**One line:** an append-only, line-by-line record of every tool call the agent considered - approved or not.

## Why it exists
If the agent ever does something wrong, there must be an unalterable record of exactly what was
asked, what tier it was, and what was decided - not a log that could have been edited afterward.

## How it works
`jarvis/safety/audit.py` opens `.data/audit.log` in **append mode only** - nothing already written
is ever rewritten or deleted. One JSON object per line (JSONL), so it can be tailed, grepped, or
read back one line at a time without loading the whole file:
```json
{"time": "2026-11-03T12:35:34Z", "tool": "send_email", "args": {"to": "a@b.com"}, "tier": "always_ask", "decision": "approved", "status": "ok"}
```
The log write lives in the same **second pass** as actually running the tool (see
[[interrupt-and-resume]]'s replay gotcha) - logging is a side effect too, so it must only happen
once a call's approval is fully resolved and nothing can pause the node again.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| JSONL file, append-only (this) | Simple, greppable, no server needed | — |
| SQLite table | Querying ("show me all denied calls last week") | More setup than a learning project's first audit log needs; could migrate later |
| Python's `logging` module | Already built in | Harder to guarantee "never truncated/rotated" without extra config; we want one unambiguous append-only file |
| Send to a remote log service | Centralized, survives a wiped PC | Overkill for a single local desktop assistant |

## Related
- [[interrupt-and-resume]]
- [[risk-tiers]]
