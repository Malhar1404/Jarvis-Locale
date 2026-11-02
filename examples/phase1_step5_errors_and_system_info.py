"""Phase 1, step 5: a real system tool, and tool errors sent back to the model as text.

Run with:  uv run python examples/phase1_step5_errors_and_system_info.py
"""

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from jarvis.llm import make_llm
from jarvis.tools.basic import divide, get_system_info, get_time, multiply
from jarvis.tools.runner import run_tool

tools = [get_time, multiply, divide, get_system_info]
tools_by_name = {t.name: t for t in tools}

llm = make_llm().bind_tools(tools)  # reasoning is off by default: clean, fast answers

system = ChatPromptTemplate.from_messages(
    [("system", "You are Jarvis, a helpful assistant on the user's PC. Be short and clear.")]
)


def ask(question: str) -> None:
    print(f"\n=== {question}")
    messages: list[BaseMessage] = system.invoke({}).to_messages() + [HumanMessage(question)]

    ai_message = llm.invoke(messages)
    messages.append(ai_message)

    for call in ai_message.tool_calls:
        tool_message = run_tool(call, tools_by_name)  # never raises: errors come back as text
        print(f"  [tool {call['name']}] status={tool_message.status}")
        print(f"  {tool_message.content}")
        messages.append(tool_message)

    final = llm.invoke(messages)
    print(f"\n  JARVIS: {final.content}")


# ask("How much battery do I have, and how busy is my CPU?")
# We tell the model to use the tool, so the crash really happens and we see how it reacts.
ask("Use the divide tool to divide 10 by 0.")
