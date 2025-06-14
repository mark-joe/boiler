# Adapted from official ntptime by Peter Hinch July 2022
# The main aim is portability:
# Detects host device's epoch and returns time relative to that.
# Basic approach to local time: add offset in hours relative to UTC.
# Timeouts return a time of 0. These happen: caller should check for this.
# Replace socket timeout with select.poll as per docs:
# http://docs.micropython.org/en/latest/library/socket.html#socket.socket.settimeout

# up to 2.6 sec/day drift

import socket
import struct
import select
import time
import machine
# from time import gmtime

# (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
# (date(1970, 1, 1) - date(1900, 1, 1)).days * 24*60*60
NTP_DELTA = 3155673600 if time.gmtime(0)[0] == 2000 else 2208988800

# The NTP host can be configured at runtime by doing: ntptime.host = 'myhost.org'
host = "pool.ntp.org"
# host = "0.nl.pool.ntp.org"

def gettime(hrs_offset=0):  # Local time offset in hrs relative to UTC
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    try:
        addr = socket.getaddrinfo(host, 123)[0][-1]
    except OSError:
        return 0
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    poller = select.poll()
    poller.register(s, select.POLLIN)
    try:
        s.sendto(NTP_QUERY, addr)
        if poller.poll(1000):  # time in milliseconds
            msg = s.recv(48)
            val = struct.unpack("!I", msg[40:44])[0]  # Can return 0
            return max(val - NTP_DELTA + hrs_offset * 3600, 0)
    except OSError:
        pass  # LAN error
    finally:
        s.close()
        
    return 0  # Timeout or LAN error occurred

def settime(wdt=None):
    N = 10
    while True:
        if wdt != None: wdt.feed()
        t=gettime()  # in unix epoch seconds
        print("output ntp", t)
        if t == 0:
            print("No ntp reaction")
            if N == 0: break
            N = N - 1
            time.sleep(0.5)
            continue
        else:
            tm = time.gmtime(t) # datetime 8 tuple record, RTC can only be set by this tuple
            machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
            print("-> NTP used to set RTC", time.localtime())
            break

