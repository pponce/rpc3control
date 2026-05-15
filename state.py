#!/usr/bin/env python3

import sys
import time
import fcntl
import os
from rpc3Control import rpc3Control, load_credentials

# Configuration
# Use absolute paths to ensure it works regardless of where Homebridge calls it from
BASE_DIR = '/var/lib/homebridge/rpc3control'
LOCK_FILE = os.path.join(BASE_DIR, 'telnetrunning.txt')
CRED_FILE = os.path.join(BASE_DIR, '.credentials')
CACHE_TTL = 7200  # 2 hours
try:
    OUTLET = int(sys.argv[1])
except (IndexError, ValueError):
    sys.stderr.write("Usage: state.py <outlet_number>\n")
    sys.exit(1)

def get_cached_data():
    if not os.path.exists(LOCK_FILE):
        return 0, False, {}
    try:
        with open(LOCK_FILE, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            lines = f.readlines()
            fcntl.flock(f, fcntl.LOCK_UN)
            if not lines: return 0, False, {}
            header = lines[0].split(',')
            ts = int(header[0]) // 1000
            needs_update = (header[1].strip() == "updated")
            status_data = {}
            for line in lines[1:]:
                parts = line.split(',')
                if len(parts) >= 2:
                    status_data[int(parts[0])] = parts[1].strip()
            return ts, needs_update, status_data
    except Exception as e:
        sys.stderr.write(f"Cache Read Error: {e}\n")
        return 0, False, {}

def update_cache_via_telnet():
    try:
        lock_fd = open(LOCK_FILE, 'a+')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        lock_fd.close()
        return False

    try:
        (rpc_host, user, pw, whitelist) = load_credentials(CRED_FILE)
        r = rpc3Control(rpc_host, user, pw)
        r.outlet_status(1) 
        return True
    except Exception as e:
        sys.stderr.write(f"Telnet Update Error: {e}\n")
        return False
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

# --- MAIN ---
try:
    timestamp, needs_update, status_map = get_cached_data()
    now = time.time()
    delta = now - timestamp

    if not status_map or delta > CACHE_TTL or needs_update:
        did_update = update_cache_via_telnet()
        if not did_update:
            # Wait loop for other process to finish
            for _ in range(30):
                time.sleep(0.5)
                _, needs_update, status_map = get_cached_data()
                if not needs_update and status_map:
                    break
        else:
            _, _, status_map = get_cached_data()

    # Get status and print to STDOUT
    final_status = status_map.get(OUTLET, "False")
    print(final_status)
    sys.exit(0) # Explicit Success

except Exception as e:
    sys.stderr.write(f"Fatal Error in state.py: {e}\n")
    sys.exit(1) # Explicit Failure
