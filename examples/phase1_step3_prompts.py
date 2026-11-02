"""Phase 1, step 3: system prompts, prompt templates, and the `|` chain.

Run with:  uv run python examples/phase1_step3_prompts.py
"""

from datetime import date

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from jarvis import config
from jarvis.tools.basic import get_time, multiply

llm = ChatOllama(model=config.MODEL, temperature=0).bind_tools([get_time, multiply])

# A template with blanks: {user_name}, {today}, {question}. They are filled in at run time.
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are Jarvis, a helpful assistant running locally on {user_name}'s PC. "
            "Today is {today}. Be short and clear. "
            "Use a tool only when it is really needed. For chat, jokes and general "
            "knowledge, just answer normally.",
        ),
        ("human", "{question}"),
    ]
)

# The pipe: fill the template, then send the result to the model.
chain = prompt | llm

# Look at what the template produces BEFORE it reaches the model.
filled = prompt.invoke({"user_name": "Jatin", "today": date.today(), "question": "Hi!"})
print("Messages the model will receive:")
for m in filled.messages:
    print(f"  {type(m).__name__:14} {m.content!r}")

questions = [
    "Tell me a one-line joke.",  # step 1: the model said "I don't have a joke tool"
    "What is 123456 times 654321?",  # should still use a tool
    "Who are you and where do you run?",  # answered from the system prompt
]

for q in questions:
    reply = chain.invoke({"user_name": "Jatin", "today": date.today(), "question": q})
    print(f"\nQUESTION: {q}")
    print(f"  content:    {reply.content!r}")
    print(f"  tool_calls: {reply.tool_calls}")
