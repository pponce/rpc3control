#!/usr/bin/env python3

from pexpect import *
import sys
import re
import syslog
import time
import os
import fcntl

class rpc3ControlError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)

class rpc3Control:
    child = None
    status = {}
    name = {}
    statuscached = False

    def __init__(self, hostname, user=None, password=None, debug=False):
        self.hostname = hostname
        self.user = user
        self.password = password
        self.debug = debug
        self.connect()
        self.child.delaybeforesend = .05

        # 1. Clear the initial banner noise
        self.child.expect([".*Unit ID: (.*)", TIMEOUT], timeout=2)
        
        # 2. Wake up PDU
        self.child.send("\r")
        
        # 3. Handle prompt
        idx = self.child.expect(["Enter username>", "Enter Selection>", TIMEOUT], timeout=10)

        if idx == 0:
            self.child.send(f"{user}\r")
            p_idx = self.child.expect(["Enter password>", "Enter Selection>", TIMEOUT], timeout=5)
            if p_idx == 0:
                self.child.send(f"{password}\r")
                self.child.expect("Enter Selection>", timeout=5)
        elif idx == 2:
            self.child.send("MENU\r")
            self.child.expect("Enter Selection>", timeout=5)

    def connect(self):
        if self.child is None:
            # Added encoding here to handle string/byte conversion automatically
            self.child = spawn(f"telnet {self.hostname}", encoding='utf-8', codec_errors='ignore')
            self.child.expect(["Connected to", EOF, TIMEOUT], timeout=5)
        if self.debug:
            # In Python 3, if encoding is set in spawn, we use sys.stdout
            self.child.logfile = sys.stdout

    def outlet(self, outlet_number, state):
        if state not in ("on", "off", "reboot"):
            self.child.send("6\r")
            self.child.terminate()
            raise rpc3ControlError('Invalid outlet state')

        if not (1 <= int(outlet_number) <= 8):
            self.child.send("6\r")
            self.child.terminate()
            return None

        self.es("Enter Selection>", "1")
        self.child.expect('Type "Help" for a list of commands', timeout=5)
        self.es("RPC-3>", f"{state} {outlet_number}", timeout=10)
        self.child.expect('Type "Help" for a list of commands', timeout=5)
        self.es("RPC-3>", "MENU")
        
        self.statuscached = False
        self.logout()
        return True

    def es(self, str_expect, str_send, timeout=3):
        result = self.child.expect([str_expect, EOF, TIMEOUT], timeout=timeout)
        if result == 0:
            self.child.send(f"{str_send}\r")
            return
        raise rpc3ControlError(f"Error waiting for '{str_expect}'")

    def logout(self):
        if self.child:
            self.child.send("6\r")
            try:
                self.child.expect(EOF, timeout=2)
            except:
                pass
            self.child.terminate()
            self.child = None

    def outlet_status(self, outlet_number):
        self.child.send("1\r")
        idx = self.child.expect(['Type "Help" for a list of commands', TIMEOUT], timeout=10)
        
        if idx == 1:
            return False

        # full_text is already a string because of spawn encoding
        full_text = self.child.before
        
        pattern = r'(\d+)\s+([A-Za-z0-9\-_]+)\s+(\d+)\s+(On|Off)'
        found_any = False
        
        for line in full_text.splitlines():
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                o_num = int(match.group(3))
                self.status[o_num] = match.group(4).strip().lower() == "on"
                self.name[o_num] = match.group(2).strip()
                found_any = True

        self.update_status_file(outlet_number)
        self.child.send("\r") 
        return self.status.get(outlet_number, False)

    def update_status_file(self, outlet_number):
        lock_filename = '/var/lib/homebridge/rpc3control/telnetrunning.txt'
        try:
            with open(lock_filename, 'w') as frunning:
                sttime = str(int(time.time() * 1000))
                frunning.write(f"{sttime},idle,\n") 
                for i in range(1, 9):
                    s = self.status.get(i, "Unknown")
                    n = self.name.get(i, "Unknown")
                    frunning.write(f"{i},{s},{n}\n")
        except Exception as e:
            if self.debug: print(f"WRITE ERROR: {e}")

def load_credentials(credentials):
    try:
        with open(credentials, 'r') as f:
            line = f.readline().rstrip()
            parts = line.split(":", 3)
            return (parts[0], parts[1], parts[2], parts[3].split(",") if len(parts) > 3 else [])
    except Exception as e:
        sys.stderr.write(f"FATAL: Credential error: {e}\n")
        sys.exit(1)
