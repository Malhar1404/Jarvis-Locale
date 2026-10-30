"""Phase 1, step 2: the full tool-calling round trip, done by hand.

    question -> model asks for a tool -> WE run it -> we send the result back -> model answers

Run with:  uv run python examples/phase1_step2_tool_roundtrip.py
"""

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_ollama import ChatOllama

from jarvis import config
from jarvis.tools.basic import get_time, multiply

tools = [get_time, multiply]
tools_by_name = {t.name: t for t in tools}  # lets us find a tool from the name the model gives us

llm = ChatOllama(model=config.MODEL, temperature=0).bind_tools(tools)


def show(messages: list[BaseMessage]) -> None:
    """Print the conversation so you can see exactly what the model is sent."""
    for m in messages:
        extra = f"  tool_calls={m.tool_calls}" if getattr(m, "tool_calls", None) else ""
        print(f"  {type(m).__name__:13} {str(m.content)!r}{extra}")


def ask(question: str) -> None:
    print(f"\n=== {question}")
    messages: list[BaseMessage] = [HumanMessage(question)]

    # Round 1: the model reads the question and may ask for tools.
    ai_message = llm.invoke(messages)
    messages.append(ai_message)  # keep its reply: the next call needs to see the request

    # We run each requested tool. The model never runs anything itself.
    for call in ai_message.tool_calls:
        tool = tools_by_name[call["name"]]
        result = tool.invoke(call["args"])
        print(f"  [we ran] {call['name']}({call['args']}) -> {result}")
        # The tool_call_id ties this result to the request it answers.
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    # Round 2: the model sees the tool results and writes the final answer in words.
    final = llm.invoke(messages)
    messages.append(final)

    print("\n  Conversation sent to / received from the model:")
    show(messages)


ask("What is 123456 times 654321?")
ask("What time is it, and what is 12 times 12?")  # two tools in one reply
