#!/usr/bin/env python3

import sys
import re
import syslog
import time
import os
import errno
import datetime
import fcntl
import shutil
from rpc3Control import *

RPC=None
#RPCUSER= str(sys.argv[2])
RPCUSER= None
RPCPASS=None
OUTLET= int(sys.argv[1])
COMMAND= str(sys.argv[3])

def file_exists(path, filename):
        for file_or_folder in os.listdir(path):
                if file_or_folder == filename:
                        return True
        return False

(RPC, RPCUSER, RPCPASS, WHITELIST) = load_credentials("/var/lib/homebridge/rpc3control/.credentials")

RPCUSER= None
#RPCUSER= str(sys.argv[2])

#telnet into unit and turn off outlet
r = rpc3Control(RPC, RPCUSER)
r.outlet(OUTLET, COMMAND)

lock_filename = 'telnetrunning.txt'
fileexists = file_exists("/var/lib/homebridge/rpc3control/", lock_filename)

#if status file exists, read it and update timestamp and outlet status for the turned off outlet. Also mark the file with updated status flag.
if (fileexists):
        my_file = open(lock_filename,'r')
        statearray = [line.split(',') for line in my_file]
        sttime = str(int(round(time.time() * 1000)))
        statearray[0][0] = sttime
        statearray[0][1] = "updated"
        statearray[OUTLET][1] = "False"
        my_file.close()
        with open(lock_filename,'w') as my_file:
                while True:
                        try:
                                fcntl.flock(my_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                                break
                        except IOError as e:
                                # raise on unrelated IOErrors
                                if e.errno != errno.EAGAIN:
                                        raise
                                else:
                                        time.sleep(0.05)
                my_file.write(statearray[0][0] + ","  + statearray[0][1] + ",\r\n")
                i=1
                while i<=8:
                        my_file.write(statearray[i][0] + ","  + statearray[i][1] + ","  + statearray[i][2])
                        i=i+1
                fcntl.flock(my_file, fcntl.LOCK_UN)
                my_file.close()
                sys.exit()
