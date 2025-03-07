#!/bin/env python

# WARN: This works *except* doesn't handle the outputs properly.
# TODO: Query the count by output.

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
handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
log.addHandler(handler)
SOCKET = os.environ["NIRI_SOCKET"]

# SOCKET = "/tmp/recorder-sock.sock"
# default tooltip
# DEF_TT = "Click to record screen. Right-click to record region."
# default text
# DEF_TEXT = "rec"

class Workspace:
    def __init__(self, id: int, output: str) -> None:
        self.id = id
        self.windows: set[int] = set()
        self.output = output
    @override
    def __str__(self) -> str:
        return str(list(self.windows))
    def add(self, id):
        self.windows.add(id)
    def remove(self, id):
        self.windows.remove(id)
    def query(self, id) -> bool:
        return id in self.windows
    def change_output(self, new: str):
        self.output = new
    def count(self) -> int:
        return len(self.windows)

class State:
    def __init__(self):
        self.active_workspace: int = 0
        # output name -> workspace: id -> window count
        self.workspaces: dict[int, Workspace] = {}
        self.first_run = True
    @override
    def __str__(self) -> str:
        s = ""
        s += f"active: {self.active_workspace}\n"
        for id, ws in self.workspaces.items():
            s += f"id: {id}, win: {ws}\n"
        return s
    def set_active(self, id: int):
        self.active_workspace = id
    def update_workspaces(self, arr: list[dict]):
        ids = []
        for ws in arr:
            id = ws["id"]
            if id not in self.workspaces:
                self.workspaces[id] = Workspace(id, ws["output"])
            ids.append(id)
            if ws["is_active"]:
                self.active_workspace = id
        for id in self.workspaces.keys():
            if id not in ids:
                self.workspaces.pop(id)
    def add_window(self, workspace_id: int, window_id: int):
        self.workspaces[workspace_id].add(window_id)
    def remove_window(self, window_id: int):
        for workspace in self.workspaces.values():
            if workspace.query(window_id):
                workspace.remove(window_id)
                return
    def update_windows(self, arr: list[dict]):
        for win in arr:
            window_id: int = win["id"]
            workspace_id: int = win["workspace_id"]
            self.add_window(workspace_id, window_id)
    def get_count(self) -> int:
        return self.workspaces[self.active_workspace].count()

state = State()

def display():
    count = state.get_count()
    print(f"Windows: {count}")
    log.info(str(state))

# function handles message from socket 
def handle_message(event: dict):
    log.debug("Handling message.")
    log.debug(event)
    should_display = False
    match next(iter(event)):
        case "WorkspacesChanged":
            workspaces : list[dict] = event["WorkspacesChanged"]["workspaces"]
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
                state.set_active(ev["id"])
                log.info("Changed active workspace.")
                should_display = True
        case "WindowOpenedOrChanged":
            window = event["WindowOpenedOrChanged"]["window"]
            window_id, workspace_id = window["id"], window["workspace_id"]
            state.add_window(workspace_id, window_id)
            log.info("Updated window.")
            should_display = True
        case "WindowClosed":
            # TODO: update Workspace to track window IDs
            ev = event["WindowClosed"]
            id: int = ev["id"]
            state.remove_window(id)
            log.info("Removed window.")
            should_display = True
    if should_display:
        display()

# start the server
def server():
    # pointer to this event loop
    # open our socket
    log.info(f"Connecting to Niri socket @ {SOCKET}")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(SOCKET)
        # needed for async
        client.sendall('"EventStream"'.encode() + b'\n')
        client.shutdown(socket.SHUT_WR)

        # only one connection at a time
        # server.listen(1)
        log.info("Connection successful, starting event loop.")
        # main loop; runs until waybar exits
        while True:
            # receive data from socket
            data = client.recv(4096)
            if not data:
                log.debug("No data!")
            # log.debug(data)
            for line in data.split(b"\n"):
                if line.strip():
                    try:
                        event = json.loads(line)
                        handle_message(event)
                    except json.JSONDecodeError:
                        print("Malformed JSON:", line.decode(errors="replace"))

# main function
def main():
    # start by outputing default contents
    # start the server
    server()

# entry point
main()
