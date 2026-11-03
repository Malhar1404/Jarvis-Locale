"""Phase 4, step 2: interrupt() and Command(resume=...) in isolation - no LLM, no tools yet.

Proves two things:
1. invoke() returns normally with an "__interrupt__" key when a node pauses - it does not raise.
2. On resume, the node function RERUNS FROM THE TOP. interrupt() just returns the resume value
   this time instead of pausing again - so anything before it in the node runs twice.

Run with:  uv run python examples/phase4_step2_interrupt_mechanics.py
"""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class State(TypedDict):
    count: int


def ask_and_increment(state: State) -> dict:
    print("  (node started running)")
    answer = interrupt("Increment the counter?")
    print(f"  (node resumed, interrupt() returned: {answer!r})")
    if answer == "yes":
        return {"count": state["count"] + 1}
    return {}


builder = StateGraph(State)
builder.add_node("step", ask_and_increment)
builder.add_edge(START, "step")
builder.add_edge("step", END)

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "demo-1"}}

print("First call - count starts at 0:")
result = graph.invoke({"count": 0}, config=config)
print("invoke() returned:", result)
question = result["__interrupt__"][0].value
print(f"\nThe agent is asking: {question!r}")

print("\nUser says yes - resuming with Command(resume='yes'):")
result = graph.invoke(Command(resume="yes"), config=config)
print("invoke() returned:", result)

print("\n--- A second thread, where the user says no ---")
config2 = {"configurable": {"thread_id": "demo-2"}}
graph.invoke({"count": 0}, config=config2)
print("\nUser says no - resuming with Command(resume='no'):")
result = graph.invoke(Command(resume="no"), config=config2)
print("invoke() returned:", result, "(count unchanged)")
