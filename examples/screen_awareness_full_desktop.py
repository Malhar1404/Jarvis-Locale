"""Inspect every connected monitor separately with the local Screen Awareness stack."""

from jarvis.tools.screen import inspect_screen

print(
    inspect_screen.invoke(
        {
            "question": "Identify the main application or activity visible on this monitor.",
            "mode": "full_desktop",
        }
    )
)
