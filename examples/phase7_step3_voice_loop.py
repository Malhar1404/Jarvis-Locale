"""Phase 7, step 3: the full voice loop, still no UI - just the terminal.

Hold the push-to-talk key (see jarvis.config.PUSH_TO_TALK_KEY, default F9), speak, then release.
Jarvis transcribes what you said, sends it through the same Agent the CLI uses (so the same
AgentEvent timeline and approval flow apply), and speaks the final reply back with Piper.

Run with:  uv run python examples/phase7_step3_voice_loop.py
"""

from jarvis.cli import render
from jarvis.config import PUSH_TO_TALK_KEY
from jarvis.setup import build_agent
from jarvis.voice.hotkey import Recorder, listen_push_to_talk
from jarvis.voice.stt import transcribe
from jarvis.voice.tts import speak

agent = build_agent()
recorder = Recorder()


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
    pending = render(agent.run(text))
    while pending is not None:
        print(f"\n  [APPROVAL NEEDED] {pending.name}({pending.args}) - tier={pending.tier}")
        answer = input("  Approve? [y/N]: ").strip().lower()
        decision = "yes" if answer == "y" else "no"
        pending = render(agent.resume(decision))
    print()

    reply = str(agent.history[-1].content)
    speak(reply)


print(f"Hold {PUSH_TO_TALK_KEY.upper()} to talk to Jarvis. Ctrl+C to quit.")
listener = listen_push_to_talk(PUSH_TO_TALK_KEY, on_press, on_release)
try:
    listener.join()
except KeyboardInterrupt:
    listener.stop()
    print("\nBye.")
