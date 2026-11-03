"""Phase 3, step 2: Agent.run(text) -> Iterator[AgentEvent], against the real model.

Same question as Phase 2's create_agent comparison (needs two genuine tool calls), but this
time we only ever look at AgentEvents - no LangGraph node names, no raw messages in sight.

Run with:  uv run python examples/phase3_step2_agent_run.py
"""

from jarvis.agent.events import Error, Thinking, Token, ToolCall, ToolResult
from jarvis.agent.runner import Agent
from jarvis.tools.basic import divide, get_system_info, get_time, multiply

agent = Agent(
    tools=[get_time, multiply, divide, get_system_info],
    system_prompt="You are Jarvis. Be short and clear. Use a tool only when really needed.",
)

print("You: What is 2 x 3, and then multiply that answer by 10?")
print("Jarvis: ", end="", flush=True)

for event in agent.run("What is 2 x 3, and then multiply that answer by 10?"):
    match event:
        case Thinking():
            pass  # could show a spinner per node in a real UI; too noisy to print here
        case Token(text=text):
            print(text, end="", flush=True)
        case ToolCall(name=name, args=args):
            print(f"\n  [asking for: {name}({args})]", end="")
        case ToolResult(name=name, content=content, status=status):
            print(f"\n  [{status}: {name} -> {content}]", end="")
        case Error(message=message):
            print(f"\n  [ERROR: {message}]", end="")

print("\n\nFinal history has", len(agent.history), "messages.")
