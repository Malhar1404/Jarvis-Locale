"""Terminal front-end: renders the Agent's AgentEvent stream as a timeline.

This file knows nothing about LangGraph - no node names, no stream modes, no raw messages.
That's the point of Phase 3: swap this module for the future Qt UI and nothing in jarvis.agent
has to change.
"""

from jarvis.agent.events import Error, Thinking, Token, ToolCall, ToolResult
from jarvis.agent.runner import Agent
from jarvis.tools.basic import divide, get_system_info, get_time, multiply

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful assistant running locally on the user's PC. "
    "Be short and clear. Use a tool only when it is really needed."
)


def run() -> None:
    agent = Agent(tools=[get_time, multiply, divide, get_system_info], system_prompt=SYSTEM_PROMPT)

    print("Jarvis (Phase 3 CLI) - type 'exit' to quit.\n")
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
        for event in agent.run(user_text):
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
        print("\n")
