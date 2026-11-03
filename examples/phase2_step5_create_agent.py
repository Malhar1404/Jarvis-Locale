"""Phase 2, step 5: langchain.agents.create_agent - the whole loop in one call.

Compares our hand-built graph (build_graph) against the prebuilt helper on the SAME question
that needed two genuine trips through the loop. Both should produce the same shape of messages.

Run with:  uv run python examples/phase2_step5_create_agent.py
"""

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from jarvis.agent.graph import build_graph
from jarvis.llm import make_llm
from jarvis.tools.basic import divide, get_system_info, get_time, multiply

tools = [get_time, multiply, divide, get_system_info]
question = {"messages": [HumanMessage("What is 2 x 3, and then multiply that answer by 10?")]}

ours = build_graph(tools)
# One call does what our ~40 lines in agent/graph.py do: chatbot <-> tools, looping until done.
prebuilt = create_agent(
    make_llm(),
    tools,
    system_prompt="You are Jarvis, a helpful assistant on the user's PC. Be short and clear.",
)

for label, graph in [("OUR build_graph", ours), ("create_agent", prebuilt)]:
    print(f"=== {label} ===")
    result = graph.invoke(question)
    for m in result["messages"]:
        extra = f"  tool_calls={m.tool_calls}" if getattr(m, "tool_calls", None) else ""
        print(f"  {type(m).__name__:13} {str(m.content)[:80]!r}{extra}")
    print()

print(
    "Same shape of messages from both - create_agent is OUR loop, pre-wired, plus extras\n"
    "like interrupt_before/interrupt_after (pause before/after a node runs), checkpointer\n"
    "and store params. Phase 4's approval gate will use that same interrupt mechanism."
)
