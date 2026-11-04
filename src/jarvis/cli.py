"""Terminal front-end: renders the Agent's AgentEvent stream as a timeline.

This file knows nothing about LangGraph - no node names, no stream modes, no raw messages.
That's the point of Phase 3: swap this module for the future Qt UI and nothing in jarvis.agent
has to change. Phase 4 adds one more thing a UI must handle: ApprovalRequest pauses the agent
until something calls Agent.resume("yes"/"no").
"""

from collections.abc import Iterator

from jarvis.agent.events import (
    AgentEvent,
    ApprovalRequest,
    Error,
    Thinking,
    Token,
    ToolCall,
    ToolResult,
)
from jarvis.agent.runner import Agent
from jarvis.tools.apps import open_app
from jarvis.tools.basic import divide, get_system_info, get_time, multiply
from jarvis.tools.brightness import get_brightness, set_brightness
from jarvis.tools.volume import get_volume, set_volume

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful assistant running locally on the user's PC. "
    "Be short and clear. Use a tool only when it is really needed."
)


def render(events: Iterator[AgentEvent]) -> ApprovalRequest | None:
    """Print each event as it arrives. Returns the ApprovalRequest if the agent paused on one."""
    for event in events:
        match event:
            case Thinking():
                pass  # a Qt UI could show a spinner per node here
            case Token(text=text):
                print(text, end="", flush=True)
            case ToolCall(name=name, args=args):
                print(f"\n  [asking for: {name}({args})]", end="")
            case ToolResult(name=name, content=content, status=status):
                print(f"\n  [{status}: {name} -> {content[:80]}]", end="")
            case Error(message=message):
                print(f"\n  [ERROR: {message}]", end="")
            case ApprovalRequest():
                return event
    return None


def run() -> None:
    tools = [
        get_time,
        multiply,
        divide,
        get_system_info,
        open_app,
        get_volume,
        set_volume,
        get_brightness,
        set_brightness,
    ]
    agent = Agent(tools=tools, system_prompt=SYSTEM_PROMPT)

    print("Jarvis (Phase 5 CLI) - type 'exit' to quit.\n")
    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return
        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print("Bye.")
            return

        print("Jarvis:", end="", flush=True)
        events = agent.run(user_text)
        pending = render(events)
        while pending is not None:
            print(f"\n  [APPROVAL NEEDED] {pending.name}({pending.args}) - tier={pending.tier}")
            answer = input("  Approve? [y/N]: ").strip().lower()
            decision = "yes" if answer == "y" else "no"
            pending = render(agent.resume(decision))
        print("\n")
