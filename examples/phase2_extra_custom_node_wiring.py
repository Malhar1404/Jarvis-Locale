"""Phase 2, extra: proving a graph node can be ANYTHING, not just an LLM or a tool runner.

No model call here on purpose - this is pure graph-wiring theory, so the trace below is
100% deterministic. Simulates "do 3 units of work, occasionally save a checkpoint to a
fake database" - the same shape Phase 4's audit-log node will use for real.

Run with:  uv run python examples/phase2_extra_custom_node_wiring.py
"""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class DemoState(TypedDict):
    count: int
    # reducers aren't just for messages: here it's string-append instead of string-replace
    log: Annotated[list[str], operator.add]


def work(state: DemoState) -> dict:
    """An ordinary node. Could just as easily call an LLM or a tool - the graph doesn't care."""
    n = state["count"] + 1
    return {"count": n, "log": [f"did work #{n}"]}


def save_to_db(state: DemoState) -> dict:
    """A 'database' node. In Phase 4 this becomes the real audit log. Here, just a print."""
    return {"log": [f"[fake db] saved checkpoint at count={state['count']}"]}


def route_after_work(state: DemoState) -> str:
    """The router function for a conditional edge. Returns a NAME, not a node - that name
    is looked up in the mapping passed to add_conditional_edges."""
    if state["count"] >= 3:
        return "done"
    if state["count"] % 2 == 0:
        return "save"
    return "loop"


builder = StateGraph(DemoState)
builder.add_node("work", work)
builder.add_node("save_to_db", save_to_db)

builder.add_edge(START, "work")
builder.add_conditional_edges(
    "work", route_after_work, {"loop": "work", "save": "save_to_db", "done": END}
)
builder.add_edge("save_to_db", "work")  # unconditional: ALWAYS go back to work after saving

graph = builder.compile()

result = graph.invoke({"count": 0, "log": []})
print("Final count:", result["count"])
print("What happened, in order:")
for line in result["log"]:
    print(" ", line)
