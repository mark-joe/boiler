import time
from machine import Pin
import ubinascii
import socket
import struct
# import utime

def blinkN(N,led=None):
    if led == None: led = Pin('LED', Pin.OUT)
#    LED = 'LED' if 'Pico W' in implementation._machine else 25 (https://github.com/peterhinch/micropython-mqtt/blob/master/mqtt_local.py)
    count = 0
    led.off()
    time.sleep(0.5)

    while count < N:
        led.on()
        time.sleep(0.1)
        led.off()    
        count = count + 1
        time.sleep(0.3)
    time.sleep(0.5)

def which_pico(wlan):
    mac = ubinascii.hexlify(wlan.config('mac'),':').decode().upper()
    print(mac)
    if mac == '28:CD:C1:04:06:F7': id = 'PicoW-05'
    if mac == '28:CD:C1:07:10:9F': id = 'PicoW-06'
    if mac == '28:CD:C1:07:0E:88': id = 'PicoW-07'
    if mac == '28:CD:C1:07:07:08': id = 'PicoW-08'
    if mac == '28:CD:C1:07:03:7D': id = 'PicoW-09'
    if mac == '28:CD:C1:04:06:6C': id = 'PicoW-10'
    if mac == 'D8:3A:DD:9D:67:B5': id = 'PicoW-11'
    if mac == 'D8:3A:DD:9D:57:29': id = 'PicoW-12'
    if mac == 'D8:3A:DD:9E:74:37': id = 'PicoW-13'
    return(id)

def get_datetime(unix=None):
    if unix==None:
        year, month, day, hour, mins, secs, weekday, yearday = time.gmtime()
    else:
        year, month, day, hour, mins, secs, weekday, yearday = time.gmtime(unix)
    date = "%d-%02d-%02d" % (year, month, day)
    tme = "%02d:%02d:%02d" % (hour, mins, secs)
    return (date,tme)

def is_dst():
	year, month, day, hour, mins, secs, weekday, yearday = time.gmtime()
	if month < 3 or month > 10: return False
	if month > 3 or month < 10: return True
	prevSunday = day - weekday
	if month == 3: return (prevSunday >= 25)
	if month == 10: return (prevSunday < 25)
   
def set_SMPS_PWM():
    SMPS = Pin("WL_GPIO1", Pin.OUT)  # sets power save (PS) off (TP4)
    SMPS.on() 


