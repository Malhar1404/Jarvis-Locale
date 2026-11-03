"""Phase 2, step 1: the smallest possible LangGraph graph. One node, no tools, no loop.

Goal: see how state flows through a graph before we add the interesting part (tools + looping).

Run with:  uv run python examples/phase2_step1_single_node_graph.py
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from jarvis.agent.state import AgentState
from jarvis.llm import make_llm

llm = make_llm()


def chatbot(state: AgentState) -> dict:
    """A node is just a function: it reads the state and returns the part it changed.

    LangGraph calls this with the CURRENT state and merges whatever we return back in,
    using the reducer we attached to `messages` (add_messages -> append, not replace).
    """
    print(f"  [chatbot node] received {len(state['messages'])} message(s)")
    reply = llm.invoke(state["messages"])
    return {"messages": [reply]}


# 1) Describe the graph: one box, wired start -> chatbot -> end.
builder = StateGraph(AgentState)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

# 2) Compile it into something runnable. This step checks the wiring is valid.
graph = builder.compile()

# 3) Run it exactly like llm.invoke(messages), but now LangGraph manages the state.
result = graph.invoke({"messages": [HumanMessage("Say hello in one short sentence.")]})

print("\nFinal state has", len(result["messages"]), "messages:")
for m in result["messages"]:
    print(f"  {type(m).__name__}: {m.content!r}")
