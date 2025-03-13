#!/bin/env python

import sys
import os
import logging
import socket
import json
from typing import override


# helper prints dict as json string
def p(obj):
    print(json.dumps(obj), flush=True)


log = logging.getLogger()
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
# log_level = os.environ["NIRILOG"]
if "NIRILOG" in os.environ:
    handler.setLevel(logging.DEBUG)
else:
    handler.setLevel(logging.ERROR)
log.addHandler(handler)
SOCKET = os.environ["NIRI_SOCKET"]


class Window:
    def __init__(self, id: int, title: str, app_id: str) -> None:
        self.id = id
        self.title = title
        self.app_id = app_id

    @override
    def __str__(self):
        return f"{self.app_id}: {self.title}"


class Workspace:
    def __init__(self, id: int, output: str) -> None:
        self.id = id
        self.windows: dict[int, Window] = {}
        # self.windows: set[int] = set()
        self.output = output

    @override
    def __str__(self) -> str:
        return str(list(self.windows))

    def add(self, id, title: str, app_id: str):
        w = Window(id, title, app_id)
        self.windows[id] = w

    def remove(self, id):
        self.windows.pop(id)

    def query(self, id) -> bool:
        return id in self.windows

    def change_output(self, new: str):
        self.output = new

    def count(self) -> int:
        return len(self.windows)
    def get_windows(self):
        return list(self.windows.values())

class State:
    def __init__(self):
        self.focused_workspace: int = 0
        self.active_workspaces: dict[str, int] = {}
        # output name -> workspace: id -> window count
        self.workspaces: dict[int, Workspace] = {}
        self.first_run = True

    @override
    def __str__(self) -> str:
        s = ""
        s += f"focused: {self.focused_workspace}\n"
        for output, id in self.active_workspaces.items():
            s += f"{output}: {id}\n"
        for id, ws in self.workspaces.items():
            s += f"id: {id}, win: {ws}\n"
        return s

    def set_activated(self, id: int):
        output = self.workspaces[id].output
        self.active_workspaces[output] = id

    def set_focused(self, id: int):
        self.focused_workspace = id

    def update_workspaces(self, arr: list[dict]):
        ids = []
        for ws in arr:
            id = ws["id"]
            output = ws["output"]
            if id not in self.workspaces:
                self.workspaces[id] = Workspace(id, output)
            ids.append(id)
            if ws["is_focused"]:
                self.focused_workspace = id
            if ws["is_active"]:
                self.active_workspaces[output] = id
        to_pop = []
        for id in self.workspaces.keys():
            if id not in ids:
                to_pop.append(id)
        for id in to_pop:
            self.workspaces.pop(id)

    def add_window(self, workspace_id: int, window_id: int, title: str, app_id: str):
        self.workspaces[workspace_id].add(window_id, title, app_id)

    def remove_window(self, window_id: int):
        for workspace in self.workspaces.values():
            if workspace.query(window_id):
                workspace.remove(window_id)
                return

    def update_windows(self, arr: list[dict]):
        for win in arr:
            window_id: int = win["id"]
            workspace_id: int = win["workspace_id"]
            title: str = win["title"]
            app_id: str = win["app_id"]
            self.add_window(workspace_id, window_id, title, app_id)

    def get_count(self, output: str | None = None) -> int:
        if output is None:
            return self.workspaces[self.focused_workspace].count()
        else:
            id = self.active_workspaces[output]
            return self.workspaces[id].count()

    def get_windows(self, output: str | None = None, ws_id: int | None = None):
        if ws_id is None:
            if output is None:
                ws_id = self.focused_workspace
            else:
                ws_id = self.active_workspaces[output]
        return self.workspaces[ws_id].get_windows()



state = State()

def display():
    print(generate_message(), flush=True)

def generate_message() -> str:
    obj = {
        "text": generate_text(),
        "tooltip": generate_tooltip()
    }
    return json.dumps(obj)


def generate_tooltip(output=None) -> str:
    windows = state.get_windows(output)
    s = ""
    for _, w in enumerate(windows):
        s += f"{str(w)}\r\n"
    return s

def generate_text(icon="", output=None):
    count = state.get_count(output)
    out = " ".join([icon] * count)
    if log.level <= logging.DEBUG:
        log.debug(str(state))
    return out


# function handles message from socket
def handle_message(event: dict):
    log.debug("Handling message.")
    log.debug(event)
    should_display = False
    match next(iter(event)):
        case "WorkspacesChanged":
            workspaces: list[dict] = event["WorkspacesChanged"]["workspaces"]
            state.update_workspaces(workspaces)
            log.info("Updated workspaces.")
            should_display = True
        case "WindowsChanged":
            windows: list[dict] = event["WindowsChanged"]["windows"]
            state.update_windows(windows)
            log.info("Updated windows.")
            should_display = True
            # workspaces : list[dict] = event["WorkspacesChanged"]["workspaces"]
            # state.process_changed(workspaces)
        case "WorkspaceActivated":
            ev = event["WorkspaceActivated"]
            if ev["focused"]:
                state.set_focused(ev["id"])
                log.info("Changed focused workspace.")
            state.set_activated(ev["id"])
            should_display = True
        case "WindowOpenedOrChanged":
            # This event also handles window moved across workspace
            window = event["WindowOpenedOrChanged"]["window"]
            window_id, workspace_id = window["id"], window["workspace_id"]
            state.remove_window(window_id)
            title = window["title"]
            app_id = window["app_id"]
            state.add_window(workspace_id, window_id, title, app_id)
            log.info("Updated window.")
            should_display = True
        case "WindowClosed":
            # TODO: update Workspace to track window IDs
            ev = event["WindowClosed"]
            id: int = ev["id"]
            state.remove_window(id)
            log.info("Removed window.")
            should_display = True
    return should_display


# start the server
def server():
    # pointer to this event loop
    # open our socket
    log.info(f"Connecting to Niri socket @ {SOCKET}")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(SOCKET)
        # needed for async
        client.sendall('"EventStream"'.encode() + b"\n")
        client.shutdown(socket.SHUT_WR)

        # only one connection at a time
        log.info("Connection successful, starting event loop.")
        # main loop; runs until waybar exits
        while True:
            # receive data from socket
            data = client.recv(4096)
            if not data:
                log.debug("No data!")
            for line in data.split(b"\n"):
                if line.strip():
                    try:
                        event = json.loads(line)
                        if handle_message(event):
                            display()
                    except json.JSONDecodeError:
                        print("Malformed JSON:", line.decode(errors="replace"))


# main function
def main():
    # start by outputing default contents
    # start the server
    try:
        server()
    except Exception as e:
        print(e, flush=True)
        log.error(e)


# entry point
main()
