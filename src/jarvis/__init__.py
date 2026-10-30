"""Jarvis: a local voice assistant that performs everyday PC tasks."""

__version__ = "0.1.0"


def main() -> None:
    from jarvis.cli import run

    run()
