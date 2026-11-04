"""Phase 5, step 2: volume and brightness control - both AUTO tier, no LLM needed to see them work.

Run with:  uv run python examples/phase5_step2_volume_brightness.py
"""

from jarvis.tools.brightness import get_brightness, set_brightness
from jarvis.tools.volume import get_volume, set_volume

original_volume = get_volume.invoke({})
original_brightness = get_brightness.invoke({})
print(f"Starting volume: {original_volume}%, brightness: {original_brightness}%")

print("\n" + set_volume.invoke({"level": 25}))
print("Now:", get_volume.invoke({}), "%")

print("\n" + set_brightness.invoke({"level": 80}))
print("Now:", get_brightness.invoke({}), "%")

print("\nRestoring original values...")
print(set_volume.invoke({"level": original_volume}))
print(set_brightness.invoke({"level": original_brightness}))
