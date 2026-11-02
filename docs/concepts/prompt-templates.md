# Prompt templates and chains

**One line:** a message with blanks (`{user_name}`) that we fill in at run time, plus `|` to send the result straight into the model.

## Why it exists
A **system prompt** is the standing briefing the model reads first: who it is, how to behave, when to use tools.
Hard-coding it as a string works once; templates let us reuse it with different values (name, date, question).

**Example:** a form letter: "Dear {name}, today is {today}".

## How it works
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Jarvis on {user_name}'s PC. Today is {today}."),
    ("human", "{question}"),
])
chain = prompt | llm                  # LCEL: fill the template, then call the model
chain.invoke({"user_name": "Jatin", "today": date.today(), "question": "Hi!"})
```
- `prompt.invoke(...)` alone shows the exact messages the model will receive. Best way to debug prompts.
- `|` joins "Runnables" (prompts, models, parsers). LangGraph nodes are the same kind of piece.
- Observed: a system prompt removed the "I don't have a joke tool" quirk and did not stop tool use.

## Alternatives
| Option | Good for | Why we did not pick it |
|---|---|---|
| Plain f-strings | Quick scripts | No reuse; easy to mix up message roles |
| `SystemMessage` list by hand | Full control | Messy with many variables |
| LangSmith prompt hub | Versioning prompts in a team | Overkill for a solo project |
| DSPy | Auto-optimizing prompts | A different approach; not needed yet |

## Related
- [[messages]]
- [[chat-model]]
