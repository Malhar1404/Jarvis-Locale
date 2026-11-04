"""Phase 7, step 3: the full voice loop, still no UI - just the terminal.

Hold the push-to-talk key (see jarvis.config.PUSH_TO_TALK_KEY, default F9), speak, then release.
Jarvis transcribes what you said, sends it through the same Agent the CLI uses (so the same
AgentEvent timeline and approval flow apply), and speaks each sentence of the reply as soon as
it's complete (see jarvis.voice.tts.SentenceSpeaker) instead of waiting for the whole thing.

Run with:  uv run python examples/phase7_step3_voice_loop.py
"""

from collections.abc import Iterator

from jarvis.agent.events import (
    AgentEvent,
    ApprovalRequest,
    Error,
    Thinking,
    Token,
    ToolCall,
    ToolResult,
)
from jarvis.config import PUSH_TO_TALK_KEY
from jarvis.setup import build_agent
from jarvis.voice.hotkey import Recorder, listen_push_to_talk
from jarvis.voice.stt import transcribe
from jarvis.voice.tts import SentenceSpeaker

agent = build_agent()
recorder = Recorder()


def speak_and_print(events: Iterator[AgentEvent]) -> ApprovalRequest | None:
    speaker = SentenceSpeaker()
    for event in events:
        match event:
            case Thinking():
                pass
            case Token(text=text):
                print(text, end="", flush=True)
                speaker.feed(text)
            case ToolCall(name=name, args=args):
                print(f"\n  [asking for: {name}({args})]", end="")
            case ToolResult(name=name, content=content, status=status):
                print(f"\n  [{status}: {name} -> {content[:80]}]", end="")
            case Error(message=message):
                print(f"\n  [ERROR: {message}]", end="")
            case ApprovalRequest():
                speaker.flush()  # say whatever Jarvis announced before pausing for approval
                return event
    speaker.flush()
    return None


def on_press() -> None:
    print("\n[listening...]", end="", flush=True)
    recorder.start()


def on_release() -> None:
    print(" transcribing...")
    audio = recorder.stop()
    text = transcribe(audio)
    if not text:
        print("(heard nothing)")
        return

    print(f"You: {text}")
    print("Jarvis:", end="", flush=True)
    pending = speak_and_print(agent.run(text))
    while pending is not None:
        print(f"\n  [APPROVAL NEEDED] {pending.name}({pending.args}) - tier={pending.tier}")
        answer = input("  Approve? [y/N]: ").strip().lower()
        decision = "yes" if answer == "y" else "no"
        pending = speak_and_print(agent.resume(decision))
    print()


print(f"Hold {PUSH_TO_TALK_KEY.upper()} to talk to Jarvis. Ctrl+C to quit.")
listener = listen_push_to_talk(PUSH_TO_TALK_KEY, on_press, on_release)
try:
    listener.join()
except KeyboardInterrupt:
    listener.stop()
    print("\nBye.")
