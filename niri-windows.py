#!/bin/env python

import sys
import os
import logging 
import socket
import json

# helper prints dict as json string
def p(obj):
    print(json.dumps(obj), flush=True)

log = logging.getLogger()
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
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
    def __init__(self, id: int, output: str, count: int) -> None:
        self.id = id
        self.count = count
        self.output = output
    def add(self):
        self.count += 1
    def change_output(self, new: str):
        self.output = new

class State:
    def __init__(self):
        self.active_workspace: int = 0
        # output name -> workspace: id -> window count
        self.workspaces: dict[int, Workspace] = {}
        self.first_run = True
    def set_active(self, id: int):
        self.active_workspace = id
    def process_changed(self, arr: list[dict]):
        ids = []
        for ws in arr:
            id = ws["id"]
            if id not in self.workspaces:
                self.workspaces[id] = Workspace(id, ws["output"], 0)
            ids.append(id)
            if ws["is_active"]:
                self.active_workspace = id
        for id in self.workspaces.keys():
            if id not in ids:
                self.workspaces.pop(id)
        if self.first_run:
            # also set the initial counts here
            self.first_run = False
    def get_count(self) -> int:
        return self.workspaces[self.active_workspace].count
    def increment(self, id: int):
        self.workspaces[id].add()

state = State()
# function handles message from socket 
def handle_message(event: dict):
    log.info("Handling message.")
    log.debug(event)
    match next(iter(event)):
        case "WorkspacesChanged":
            workspaces : list[dict] = event["WorkspacesChanged"]["workspaces"]
            state.process_changed(workspaces)
        case "WorkspaceActivated":
            ev = event["WorkspaceActivated"]
            if ev["focused"]:
                state.set_active(ev["id"])
        case "WindowOpenedOrChanged":
            ev = event["WindowOpenedOrChanged"]
            workspace= ev["window"]["workspace_id"]
        case "WindowClosed":
            # TODO: update Workspace to track window IDs
            ev = event["WindowClosed"]
            id: int = ev["id"]

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
