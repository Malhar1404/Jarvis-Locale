# Glossary

Short definitions. Link to a concept note when one exists.

- **Chat model**: an LLM wrapper that takes a list of messages and returns a message. See [[chat-model]].
- **Message**: one turn in a conversation (System, Human, AI, Tool). See [[messages]].
- **Streaming**: receiving the reply in chunks while the model generates. See [[streaming]].
- **Tool call**: the model's request to run a function, with arguments. We run it. See [[tool-calling]].
- **System prompt**: standing instructions the model reads before the conversation. See [[prompt-templates]].
- **Chain / LCEL**: pieces joined with `|`, for example `prompt | llm`. See [[prompt-templates]].
- **Structured output**: the model fills a fixed Pydantic "form". See [[structured-output]].
- **Reasoning model**: a model that thinks before answering. See [[reasoning-models]].
- **Node**: a plain function `(state) -> dict` registered with `add_node`. Can do anything. See [[graph-nodes-and-edges]].
- **Edge**: `add_edge(A, B)` — always go from A to B. See [[graph-nodes-and-edges]].
- **Conditional edge / router function**: a function that returns a name, used to pick the next node. See [[graph-nodes-and-edges]].
- **Reducer**: a function (e.g. `add_messages`, `operator.add`) that decides how a node's returned value is merged into state, instead of replacing it. See [[graph-nodes-and-edges]].
