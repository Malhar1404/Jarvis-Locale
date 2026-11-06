"""Stops a second copy of the Jarvis window from starting. Needed now that the agent's memory
lives in one SQLite file (see jarvis.agent.runner) - two processes writing to it at once is
exactly the kind of thing that caused the double-speaking bug in Phase 7.
"""

import sys

import win32api
import win32event
import winerror

_MUTEX_NAME = "JarvisUISingleInstance"
_handle = None  # module-level so the OS handle stays open for the whole process lifetime


def acquire_or_exit() -> None:
    """Create a named OS mutex. If one already exists, another Jarvis window is already
    running - print a message and exit instead of opening a second one.

    No cleanup needed on crash: Windows releases a process's handles, mutexes included, the
    moment the process ends, however it ends.
    """
    global _handle
    _handle = win32event.CreateMutex(None, False, _MUTEX_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        print("Jarvis is already running - check your system tray.")
        sys.exit(0)
