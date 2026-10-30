# Chat model

**One line:** a LangChain object that wraps an LLM so you send it a list of messages and get a message back.

## Why it exists
Each provider (Ollama, OpenAI, Anthropic) has its own API. LangChain gives them one interface, so
the rest of the code does not change when the model does. Here it is `ChatOllama`.

## How it works
- `llm.invoke(messages)` returns one `AIMessage`.
- `llm.stream(messages)` yields `AIMessageChunk`s as they are generated. See [[streaming]].
- `llm.bind_tools([...])` tells the model which tools it may ask for. Phase 1.
- The model is stateless: you must send the whole conversation each time. See [[messages]].

## Small example
```python
from langchain_ollama import ChatOllama
llm = ChatOllama(model="qwen3:4b", temperature=0)
llm.invoke("hi").content
```

## Related
- [[messages]]
- [[streaming]]
