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
from jarvis.tools.timesheet import add_timesheet_entry, list_timesheet_tabs, read_timesheet_tab
from jarvis.tools.volume import get_volume, set_volume

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful assistant running locally on the user's PC. "
    "Be short and clear. Use a tool only when it is really needed."
)


def build_tools() -> list[BaseTool]:
    return [
        get_time,
        multiply,
        divide,
        get_system_info,
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
    ]


def build_agent(tools: list[BaseTool] | None = None) -> Agent:
    return Agent(tools=tools if tools is not None else build_tools(), system_prompt=SYSTEM_PROMPT)
