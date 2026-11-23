"""Builds the Agent with its full tool list - shared by every front-end (CLI, Qt UI, ...) so
none of them has to duplicate the tool wiring.
"""

from langchain_core.tools import BaseTool

from jarvis.agent.runner import Agent
from jarvis.tools.apps import open_app
from jarvis.tools.basic import divide, get_system_info, get_time, multiply
from jarvis.tools.brightness import get_brightness, set_brightness
from jarvis.tools.clipboard import get_clipboard, set_clipboard
from jarvis.tools.files import (
    delete_file,
    list_files,
    move_file,
    read_file,
    search_files,
    write_file,
)
from jarvis.tools.memory import list_remembered_facts, recall_fact, remember_fact
from jarvis.tools.screen import inspect_screen
from jarvis.tools.timesheet import add_timesheet_entry, list_timesheet_tabs, read_timesheet_tab
from jarvis.tools.volume import get_volume, set_volume

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful assistant running locally on the user's PC. "
    "Be short and clear. Use a tool only when it is really needed. "
    "Your bound tool definitions are the authoritative list of your capabilities: never claim "
    "that you cannot perform an action when a matching tool is available. For a direct request "
    "to change brightness or volume, call the matching set tool instead of explaining how the "
    "operating system works. "
    "For questions about the user's currently visible apps, UI, errors, or desktop, use "
    "inspect_screen. It always captures the whole desktop across every connected monitor. It "
    "returns observations from a vision model: turn those into a helpful human-readable answer, "
    "and do not present its JSON directly. "
    "Reply in plain conversational sentences only: no markdown (no **, *, #, bullet lists, code "
    "fences) and no emoji. Answer exactly what was asked, briefly, and do not add unrelated "
    "information the user did not ask for. "
    "Use remember_fact on your own whenever the user shares or corrects something about "
    "themselves worth keeping for future conversations (their name, a usual folder, a "
    "preference) - including when they correct something you got wrong, even if they do not "
    "explicitly say 'remember'. Overwrite the old value rather than keeping both. Do not use it "
    "for one-off task details. Use recall_fact or list_remembered_facts to check what you "
    "already know instead of asking the user to repeat it."
)


def build_tools() -> list[BaseTool]:
    return [
        get_time,
        multiply,
        divide,
        get_system_info,
        inspect_screen,
        open_app,
        get_volume,
        set_volume,
        get_brightness,
        set_brightness,
        get_clipboard,
        set_clipboard,
        list_files,
        read_file,
        search_files,
        write_file,
        delete_file,
        move_file,
        list_timesheet_tabs,
        read_timesheet_tab,
        add_timesheet_entry,
        remember_fact,
        recall_fact,
        list_remembered_facts,
    ]


def build_agent(tools: list[BaseTool] | None = None) -> Agent:
    return Agent(tools=tools if tools is not None else build_tools(), system_prompt=SYSTEM_PROMPT)
