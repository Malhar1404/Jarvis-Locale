# Multi-agent systems

**One line:** a "multi-agent system" is just several small graphs (or LLM calls), with one more
piece of code deciding which one runs next - nothing more mystical than that.

## Why it exists
One agent with a long system prompt and ten unrelated tools tends to get confused about which
tool to use. Splitting into specialists (one agent per job, each with its own focused prompt and
small tool list) is easier for a small local model to use correctly - and easier for us to reason
about, test, and give different risk tiers.

## Two ways to branch to multiple nodes

### 1. Deterministic routing - our own `StateGraph`
Exactly [[graph-nodes-and-edges]], just with a `mapping` that has 3+ entries instead of 2. A plain
Python function decides the route; the LLM never sees this decision being made.

```python
builder.add_conditional_edges(
    "triage",                 # node1: one LLM call that classifies the question
    route_after_triage,       # plain function -> returns a string
    {
        "billing": "billing_node",     # node1 -> node2
        "technical": "tech_node",      # node1 -> node3
        "unclear": END,
    },
)
```

`route_after_triage(state)` reads `state["messages"][-1]` and returns `"billing"` /
`"technical"` / `"unclear"` with ordinary `if/elif` - the same shape as our `has_tool_calls`.

### 2. LLM-chosen routing - "agents as tools" with `create_agent`
`create_agent` always builds the same fixed shape (one `model` node, one `tools` node) - it has
**no parameter** for "run a classifier, then hard-route." To reach the same end result with it,
each specialist becomes a whole `create_agent`, wrapped as a single `@tool` the top-level agent
can call:

```python
billing_agent = create_agent(llm, [lookup_invoice], system_prompt="You handle billing.")
tech_agent    = create_agent(llm, [restart_service], system_prompt="You handle tech support.")

@tool
def handle_billing(question: str) -> str:
    """Use for any billing, invoice, or payment question."""
    result = billing_agent.invoke({"messages": [HumanMessage(question)]})
    return result["messages"][-1].content

@tool
def handle_tech(question: str) -> str:
    """Use for any technical problem or outage."""
    result = tech_agent.invoke({"messages": [HumanMessage(question)]})
    return result["messages"][-1].content

supervisor = create_agent(llm, [handle_billing, handle_tech],
                           system_prompt="Route the user's question to the right specialist tool.")
```

`supervisor` is still just one `model`+`tools` graph. Its "tools" happen to each run a whole
other graph internally. The "triage" step is now the supervisor LLM's first tool-call choice -
no separate node, no conditional-edge dict. It reads each tool's docstring the same way it reads
`get_time`'s, and picks accordingly.

## The real tradeoff
| | Who decides the route | Reliability | When to use |
|---|---|---|---|
| Our `StateGraph` (option 1) | A Python function | Always correct - it's code, not a guess | A rule that must never be wrong (e.g. "refunds always needs human approval") |
| Agents-as-tools (option 2) | The LLM, by picking a tool | Only as good as the model's tool choice - can pick the wrong specialist | Routing is fuzzy/subjective and the convenience of `create_agent` is worth it |

This is the same "convenience vs. control" tradeoff as `create_agent` itself: less code to write,
less certainty about what it will do.

## Alternatives
| Option                                                           | Good for                                                     | Why we did not pick it (yet)                                                          |
| ---------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| Deterministic `StateGraph` routing (this)                        | A fixed, known set of branches, decided by code              | Our pick for anything safety-related (Phase 4)                                        |
| Agents-as-tools (this)                                           | Fuzzy routing, fast to build with `create_agent`             | Fine for non-risky branching once we have specialists to split out                    |
| LangGraph prebuilt "supervisor" package (`langgraph-supervisor`) | A ready-made version of agents-as-tools with handoff helpers | Separate package, not installed; writing it by hand first builds the mental model     |
| One single agent with all tools                                  | Very few tools, no real specialization needed                | What we have now (Phase 2) - fine until the tool list gets large or mixes risk levels |

## Related
- [[graph-nodes-and-edges]]
- [[tool-calling]]
