"""Phase 4, step 3: the real approval gate (risk tiers + interrupt()) - no LLM yet.

We hand-craft the tool_calls an AIMessage would produce (same principle as Phase 1 step 2's
manual tool round trip), so the gate's behavior is deterministic and easy to read. Step 4 wires
this into a live LLM through the CLI.

Run with:  uv run python examples/phase4_step3_approval_gate.py
"""

from typing import TypedDict

from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from jarvis.safety.approval import run_tool_with_approval
from jarvis.safety.tiers import RiskTier, risk_tier


@risk_tier(RiskTier.AUTO)
@tool
def get_time() -> str:
    """Fake auto tool: nothing to approve."""
    return "12:00"


@risk_tier(RiskTier.ASK_ONCE)
@tool
def open_app(name: str) -> str:
    """Pretend to open an app - ask the first time per conversation, then remember."""
    return f"opened {name}"


@risk_tier(RiskTier.ALWAYS_ASK)
@tool
def send_email(to: str, body: str) -> str:
    """Pretend to send an email - ask every single time."""
    return f"sent to {to}: {body!r}"


@risk_tier(RiskTier.NEVER)
@tool
def format_disk() -> str:
    """Pretend to format a disk - must never run."""
    return "disk formatted"


TOOLS_BY_NAME = {t.name: t for t in [get_time, open_app, send_email, format_disk]}


class State(TypedDict):
    calls: list
    results: list
    approved_once: set


def run_tools(state: State) -> dict:
    approved = set(state.get("approved_once", set()))
    results = []
    for call in state["calls"]:
        result, approved = run_tool_with_approval(call, TOOLS_BY_NAME, approved)
        results.append(result.content)
    return {"results": results, "approved_once": approved}


builder = StateGraph(State)
builder.add_node("run_tools", run_tools)
builder.add_edge(START, "run_tools")
builder.add_edge("run_tools", END)
graph = builder.compile(checkpointer=InMemorySaver())


def call(tool_name: str, **args) -> dict:
    return {"name": tool_name, "args": args, "id": f"call-{tool_name}-{args}"}


def demo(title: str, calls: list, thread_id: str, decisions: list[str]) -> None:
    print(f"\n=== {title} ===")
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"calls": calls, "results": [], "approved_once": set()}, config=config)
    decisions_iter = iter(decisions)
    while "__interrupt__" in result:
        req = result["__interrupt__"][0].value
        print(f"  [APPROVAL NEEDED] {req['name']}({req['args']}) tier={req['tier']}")
        decision = next(decisions_iter)
        print(f"  -> user answers: {decision!r}")
        result = graph.invoke(Command(resume=decision), config=config)
    print("  results:", result["results"])


demo("AUTO - never pauses", [call("get_time")], "t1", decisions=[])

demo(
    "ASK_ONCE - approve once, second call in the same turn reuses it silently",
    [call("open_app", name="Notepad"), call("open_app", name="Notepad")],
    "t2",
    decisions=["yes"],
)

demo(
    "ALWAYS_ASK - every call needs its own approval, even the same tool twice",
    [call("send_email", to="a@b.com", body="hi"), call("send_email", to="c@d.com", body="bye")],
    "t3",
    decisions=["yes", "yes"],
)

demo(
    "ALWAYS_ASK - denied: the model gets an error message back, nothing runs",
    [call("send_email", to="a@b.com", body="hi")],
    "t4",
    decisions=["no"],
)

demo(
    "NEVER - blocked immediately, no question ever asked",
    [call("format_disk")],
    "t5",
    decisions=[],
)
