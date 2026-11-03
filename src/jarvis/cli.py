"""Terminal front-end: a real streaming chat loop over the Phase 2 agent graph.

No checkpointer yet (that's Phase 8) - `history` is a plain Python list we grow ourselves,
and we resend the whole thing every turn, same principle as Phase 1's messages list.
"""

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from jarvis.agent.graph import build_graph
from jarvis.tools.basic import divide, get_system_info, get_time, multiply

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful assistant running locally on the user's PC. "
    "Be short and clear. Use a tool only when it is really needed."
)


def run() -> None:
    graph = build_graph([get_time, multiply, divide, get_system_info])
    history: list[BaseMessage] = [SystemMessage(SYSTEM_PROMPT)]

    print("Jarvis (Phase 2 CLI) - type 'exit' to quit.\n")
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

        history.append(HumanMessage(user_text))
        print("Jarvis:", end="", flush=True)

        stream = graph.stream({"messages": history}, stream_mode=["updates", "messages"])
        for mode, payload in stream:
            if mode == "messages":
                chunk, metadata = payload
                if metadata.get("langgraph_node") == "chatbot" and chunk.content:
                    print(chunk.content, end="", flush=True)
            else:  # mode == "updates": a node just finished - grow OUR history to match
                for node_name, change in payload.items():
                    for msg in change["messages"]:
                        history.append(msg)
                        if node_name == "chatbot" and getattr(msg, "tool_calls", None):
                            names = ", ".join(c["name"] for c in msg.tool_calls)
                            print(f"\n  [asking for: {names}]", end="")
                        elif node_name == "tools":
                            print(f"\n  [tool -> {str(msg.content)[:80]}]", end="")
        print("\n")
