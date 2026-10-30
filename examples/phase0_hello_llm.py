"""Phase 0: talk to a local Ollama model through LangChain.

Run with:  uv run python examples/phase0_hello_llm.py
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

MODEL = "qwen3:4b"

llm = ChatOllama(model=MODEL, temperature=0)

messages = [
    SystemMessage("You are Jarvis, a concise assistant running locally on the user's PC."),
    HumanMessage("Say hello and tell me in one sentence what you can do."),
]

# 1) One-shot call: returns a single AIMessage.
reply = llm.invoke(messages)
print("invoke ->", reply.content)
print("metadata ->", reply.response_metadata.get("eval_count"), "tokens\n")

# 2) Streaming: yields AIMessageChunks as the model generates (what the UI will use).
print("stream -> ", end="")
for chunk in llm.stream(messages):
    print(chunk.content, end="", flush=True)
print()
