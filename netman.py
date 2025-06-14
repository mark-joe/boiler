# Author: peppe8o
# Date: Jul 24th, 2022
# Version: 1.0
# https://peppe8o.com

import network, rp2
import time
from ms_utils import blinkN
import ubinascii
import machine

# https://docs.micropython.org/en/latest/library/network.WLAN.html

def connectWiFi(ssid,password,country='NL'):
   rp2.country(country)
   wlan = network.WLAN(network.STA_IF)
   mac = ubinascii.hexlify(wlan.config('mac'),':').decode()
   print('mac = ' + mac)
#   # Other things to query
#   print(wlan.config('channel')) 
#   print(wlan.config('essid'))
#   print(wlan.config('txpower'))

   wlan.active(True)
   wlan.config(pm = 0xa11140) # power save off ?
   accessPoints = wlan.scan()
   for ap in accessPoints:
       print(ap)
   print("given ssid", ssid)
   if isinstance(ssid,list): # is list of ssid's, select max dB
      maxdB=-999
      maxI=-1
      for (i,s) in enumerate(ssid):
         for ap in accessPoints:
            ap2 = ap[0].decode("utf-8") 
#            print("check",s,ap2,ap[3],ap2==s)
            if ap2 == s:
               if ap[3] > maxdB:
                  maxdB = ap[3]
                  maxI = i
      selected_ssid = ssid[maxI]
      selected_password = password[maxI]
   else:
      selected_ssid = ssid
      selected_password = password
               
   print("Try to connect to", selected_ssid)   
   # for ap in accessPoints: print(ap)
   wlan.connect(selected_ssid, selected_password)
   # Wait for connect or fail
   max_wait = 10
   while max_wait > 0:
      if wlan.status() < 0 or wlan.status() >= 3:
        break
      max_wait -= 1
      print('waiting for connection...')
      time.sleep(1)

# STAT_IDLE -- 0
# STAT_CONNECTING -- 1
# STAT_WRONG_PASSWORD -- -3
# STAT_NO_AP_FOUND -- -2
# STAT_CONNECT_FAIL -- -1
# STAT_GOT_IP -- 3

   # Handle connection error
   if wlan.status() != 3:
      print("wlan status", wlan.status())
      blinkN(10)
#      raise RuntimeError('network connection failed')
#      machine.reset()
      time.sleep(10) # watchdog or reset
      print("reset machine")
      machine.reset()
   else:
      print('connected')
      status = wlan.ifconfig()
      print(status)
      print( 'ip = ' + status[0] )
      dir(wlan)
   return wlan
