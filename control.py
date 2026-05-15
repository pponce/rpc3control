#!/usr/bin/env python3

import sys
import time
import os
import fcntl
import errno
from rpc3Control import rpc3Control, load_credentials

# Configuration
BASE_DIR = '/var/lib/homebridge/rpc3control'
LOCK_FILE = os.path.join(BASE_DIR, 'telnetrunning.txt')
CRED_FILE = os.path.join(BASE_DIR, '.credentials')

try:
    OUTLET = int(sys.argv[1])
    COMMAND = str(sys.argv[3]).lower() # 'on', 'off', or 'reboot'
except (IndexError, ValueError):
    sys.stderr.write("Usage: control.py <outlet> <user> <command>\n")
    sys.exit(1)

try:
    # 1. Execute the Hardware Command
    (rpc_host, user, pw, whitelist) = load_credentials(CRED_FILE)
    r = rpc3Control(rpc_host, user, pw)
    r.outlet(OUTLET, COMMAND)

    # 2. Update the Status File to signal state.py
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r+') as f:
                # Try to get lock for max 2 seconds
                for _ in range(40): 
                    try:
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except IOError:
                        time.sleep(0.05)
                else:
                    raise IOError("Timeout acquiring lock")

                lines = f.readlines()
                if len(lines) >= 9:
                    sttime = str(int(round(time.time() * 1000)))
                    lines[0] = f"{sttime},updated,\r\n"

                    parts = lines[OUTLET].split(',')
                    # Only update if it was on/off (not reboot)
                    if COMMAND in ["on", "off"]:
                        new_state = "True" if COMMAND == "on" else "False"
                        lines[OUTLET] = f"{OUTLET},{new_state},{parts[2]}"

                    f.seek(0)
                    f.truncate()
                    f.writelines(lines)

                fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            sys.stderr.write(f"Status file update skipped: {e}\n")

    # 3. Final Output for Homebridge
    # Echoing the command back (e.g., "ON" or "OFF") tells Homebridge it worked.
    print(COMMAND.upper())
    sys.exit(0)

except Exception as e:
    sys.stderr.write(f"Fatal Error in control.py: {e}\n")
    sys.exit(1)
