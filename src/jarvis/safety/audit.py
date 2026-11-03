"""Append-only audit log: every tool call the agent considers - approved or not - gets one line
here. CLAUDE.md: runtime data goes in .data/ (gitignored). "Append-only" means we only ever open
in append mode; nothing already written is ever rewritten or deleted.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

AUDIT_LOG_PATH = Path(".data/audit.log")


def log_tool_call(
    *,
    name: str,
    args: dict,
    tier: str,
    decision: Literal["auto", "approved", "denied", "blocked"],
    status: Literal["ok", "error"],
) -> None:
    """One JSON object per line (JSONL) - easy to tail, grep, or read back one line at a time."""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": datetime.now(UTC).isoformat(),
        "tool": name,
        "args": args,
        "tier": tier,
        "decision": decision,
        "status": status,
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
