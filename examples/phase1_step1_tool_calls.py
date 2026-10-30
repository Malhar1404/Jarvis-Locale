"""Phase 1, step 1: see what a tool looks like to the model, and what the model sends back.

The model does NOT run any tool here. It only says which tool it wants and with what arguments.

Run with:  uv run python examples/phase1_step1_tool_calls.py
"""

from langchain_ollama import ChatOllama

from jarvis import config
from jarvis.tools.basic import get_time, multiply

tools = [get_time, multiply]

# 1) What the model is shown for each tool: a name, a description, and an argument schema.
#    The description comes from the function's docstring. The schema comes from the type hints.
for t in tools:
    print(f"TOOL: {t.name}")
    print(f"  description: {t.description}")
    print(f"  arguments:   {t.args}\n")

# 2) Give the tools to the model. bind_tools returns a new model that knows about them.
llm = ChatOllama(model=config.MODEL, temperature=0).bind_tools(tools)

# 3) Ask questions and look at the raw reply. Look at .tool_calls, not .content.
questions = [
    "What time is it right now?",
    "What is 123456 times 654321?",
    "Tell me a one-line joke.",  # no tool needed, so the model should just answer
]

for q in questions:
    reply = llm.invoke(q)
    print(f"QUESTION: {q}")
    print(f"  content:    {reply.content!r}")
    print(f"  tool_calls: {reply.tool_calls}\n")
