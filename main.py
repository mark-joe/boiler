import network
import utime
from machine import Pin, ADC, WDT
from netman import connectWiFi
from ms_utils import blinkN, which_pico, get_datetime, set_SMPS_PWM, is_dst
import ntptime2
from secrets import secrets
from umqttsimple import MQTTClient
import onewire
import ds18x20
import json
import collections
import math

VERSION = '20250613'
DEBUG = False

PROJECT = 'boiler'
keepalive = 600 # mqtt
use_WDT = True
if DEBUG: 
    keepalive = 60
    use_WDT = False
HEATING_POWER = 1150
NTP_UPDATE_INTERVAL = 86400 # number of seconds
USE_SALDERING = True  # make sure boiler is warm at six pm anyway
TARGET_TEMP = 75.0

def mqtt_connect(): 
    mqtt_server = secrets['mqtt_server']
    client = MQTTClient(pico_id, mqtt_server, keepalive=keepalive, user=secrets['mqtt_user'], password=secrets['mqtt_password'])
    client.connect()
    print('Connected to %s MQTT Broker'%(mqtt_server))
    blinkN(5,led)
    return client

def reconnect():
    print('Failed to connect to MQTT Broker. Rebooting ...')
    utime.sleep(10)
    machine.reset()
    
def sub_cb(topic, msg):
    global last_production_value
    global p1_timestamp, p1_timestamp_utc
    global last_p1_message
#    global updown
        
    if use_WDT: wdt.feed()
    if topic.decode('utf-8') == 'p1monitor/smartmeter/production_kw':
        payload = msg.decode('utf-8')
        last_production_value = float(msg) * 1000.0
        last_p1_message = utime.time()
    if topic.decode('utf-8') == 'p1monitor/smartmeter/timestamp_local':
        p1_timestamp = msg.decode('utf-8')
    if topic.decode('utf-8') == 'p1monitor/smartmeter/timestamp_utc':
        p1_timestamp_utc = int(msg)
#    if topic.decode('utf-8') == 'sun/updown':
#        updown = json.loads(msg)        
            
    if DEBUG: print("New message on topic {}".format(topic.decode('utf-8')))
    if DEBUG: print("Message: {}".format(msg.decode('utf-8')))

set_SMPS_PWM()
led = Pin('LED', Pin.OUT)
blinkN(2, led)

p = Pin(15, Pin.IN, Pin.PULL_UP)
ow = onewire.OneWire(p)
ds = ds18x20.DS18X20(ow)
roms = ds.scan()
if len(roms) == 0: PROJECT = PROJECT + '-test'

bootlog = "boot.txt"
fp = open(bootlog,"a")
fp.write("restart -- ")

wlan = connectWiFi(secrets['wlan_ssid'],secrets['wlan_password'],secrets['wlan_country'])
pico_id = which_pico(wlan)
print("pico_id", pico_id)
fp.write("wifi is up -- ")
blinkN(3,led)
    
ntptime2.settime()
(date,tme)=get_datetime()
last_ntp_update = utime.time()
fp.write("ntp: " + date + " " + tme + ' (UTC) -- ')
last_boot = date + " " + tme + ' (UTC)'
blinkN(4,led)

try:
    client = mqtt_connect()
except OSError as e:
    reconnect()

fp.write("mqtt is up\n")
fp.close()

heater_switch = Pin(6, Pin.OUT)
heater_switch.off()

HEATING_ON = Pin(22, Pin.IN)

last_production_value = 0
p1_timestamp = ''
p1_timestamp_utc = utime.time()
last_p1_message = utime.time()
# updown = None
start_time_string = ''

client.set_callback(sub_cb)
topic_sub = b'p1monitor/smartmeter/production_kw'
client.subscribe(topic_sub, qos=0)
topic_sub = b'p1monitor/smartmeter/timestamp_local'
client.subscribe(topic_sub, qos=0)
topic_sub = b'p1monitor/smartmeter/timestamp_utc'
client.subscribe(topic_sub, qos=0)
# topic_sub = b'sun/updown'
# client.subscribe(topic_sub, qos=0)
wdt = None
if use_WDT: wdt = WDT(timeout=5000)  # max 8388 millisecs
last_publish = utime.time()     # in seconds

SOLAR_OK_COUNTER = 0
SOLAR_DOWN_COUNTER = 10
SALDERING_ON = False
SOLAR_OK = False

while True:  # loop takes about 2 seconds
    try:
        while client.check_msg() != None: utime.sleep(0.2)
    except OSError as error:
        (date,tme)=get_datetime()
        fp = open("errors.txt","a")
        fp.write(date + " " + tme + " " + error + "\n")
        fp.close()
        print(error)
    
    if use_WDT: wdt.feed()

    diff_publish = utime.time() - last_publish
    if diff_publish > (keepalive / 10):
        if DEBUG: print("time for a publish", diff_publish)
        last_publish = utime.time()
        client.publish("%s/last_boot"%PROJECT, last_boot, retain=False, qos=0)
        client.publish("%s/last_temperature"%PROJECT, "%.1f" % temp, retain=False, qos=0)
        client.publish("%s/wlan_ssid"%PROJECT, wlan.config('ssid'), retain=False, qos=0)
        client.publish("%s/wlan_RSSI"%PROJECT, str(wlan.status('rssi')), retain=False, qos=0)
        client.publish("%s/wlan_ip"%PROJECT, str(wlan.ifconfig()[0]), retain=False, qos=0)
        client.publish("%s/whoami"%PROJECT, pico_id, retain=False, qos=0)
        (date,tme)=get_datetime()
        client.publish("%s/heartbeat"%PROJECT, date + " " + tme + ' (UTC)')
        client.publish("%s/p1_timestamp"%PROJECT, p1_timestamp, retain=False, qos=0)
        client.publish("%s/last_production_value"%PROJECT, str(last_production_value), retain=False, qos=0)
        client.publish("%s/solar_ok"%PROJECT, str(int(SOLAR_OK)), retain=False, qos=0)
        client.publish("%s/heating_on"%PROJECT, str(onoff), retain=False, qos=0)
        client.publish("%s/start_time"%PROJECT, start_time_string, retain=False, qos=0)
#        if updown != None:
#            client.publish("%s/sunset"%PROJECT, updown['sunset'] + ' (UTC)', retain=False, qos=0)
        client.publish("%s/SALDERING_ON"%PROJECT, str(int(SALDERING_ON)), retain=False, qos=0)

        dic = collections.OrderedDict()
        dic['last_boot']=last_boot
        dic['last_temperature']=temp
        dic['wlan_ssid']=wlan.config('ssid')
        dic['wlan_RSSI']=wlan.status('rssi')
        dic['wlan_status']=wlan.status()
        dic['wlan_ip']=str(wlan.ifconfig()[0])
        dic['whoami']=pico_id
        dic['version']=VERSION
        dic['heartbeat']=date + " " + tme + ' (UTC)'
        dic['p1_timestamp']= p1_timestamp
        dic['last_production_value']=last_production_value
        dic['solar_ok']=SOLAR_OK
        dic['heating_on']=onoff
        dic['start_time']= start_time_string
#        if updown != None:
#            dic['sunset']=updown['sunset'] + ' (UTC)'
        dic['SALDERING_ON']=SALDERING_ON

        s = json.dumps(dic)
        client.publish("%s/json"%PROJECT, s, retain=False, qos=1) # QOS set to 1 to verify connection
	
    if len(roms)>0:
        try:
            ds.convert_temp()  # max 750 ms it takes
            utime.sleep(1.0)
            temp = ds.read_temp(roms[0])
        except Exception as error:
            (date,tme)=get_datetime()
            fp = open("errors.txt","a")
            fp.write(date + " " + tme + " " + error + "\n")
            fp.close()
            print(error)
            temp = -1.0
    else:
        temp = 55.5
        utime.sleep(1.0)

    onoff = HEATING_ON.value() # is integer
    prod = last_production_value + onoff * HEATING_POWER
    # bit tricky, can be forced on while not enough generation
    # in that case prod is EXACTLY HEATING_POWER and
    # will NOT PASS TEST for enough generation
    if DEBUG:
        print("prod", last_production_value, "onoff:", onoff, "Actual production:", prod)

# is p1 info actually still valid?
    unix_time = utime.time()
    if DEBUG:
        d = unix_time - last_p1_message
        print("seconds since last p1 message", d)

    if unix_time > (last_p1_message + 600): # p1 data more than 10 minutes old...
        prod = 9999 # allow for heating
        
    if unix_time > (last_ntp_update + NTP_UPDATE_INTERVAL):
        pre = utime.time()
        ntptime2.settime(wdt)  # wdt is on
        delta = utime.time() - pre
        last_ntp_update = utime.time()
        (date,tme)=get_datetime()
        if DEBUG:
            print("ntp post update: delta:%d " % delta + date + " " + tme + ' (UTC) -- ')
        fp = open(bootlog,"a")
        fp.write("ntp post update: delta:%d " % delta + date + " " + tme + ' (UTC) \n')
        fp.close()

# First switch on/off based on saldering (heat boiler before 18 pm, buy no earlier than required)
# Secondly, if prod OK, set on

    SALDERING_ON = False
    start_time_string = "no need to heat"
    if USE_SALDERING: 
        LT18h = math.floor(unix_time / 86400) * 86400 + 17 * 3600 - int(is_dst()) * 3600
        joules = (TARGET_TEMP - temp) * 4.2 * 80 * 1000
        if joules < 0.0: joules = 0.0
        seconds_to_heat = int(joules / HEATING_POWER)
        if seconds_to_heat > 0:
            start_time = LT18h - seconds_to_heat # - 3600
            (d,t) = get_datetime(start_time)
            start_time_string = d + " " + t + " (UTC)"
            if unix_time > start_time and unix_time < LT18h: SALDERING_ON = True
            
    if prod > HEATING_POWER: 
        SOLAR_OK_COUNTER = SOLAR_OK_COUNTER + 1
        SOLAR_OK = (SOLAR_OK_COUNTER > 10)  # takes about 20 seconds
        if SOLAR_OK: SOLAR_DOWN_COUNTER = 10
    else:
        if SOLAR_OK == True:  # was ok, now prod not enough, shutting down in 10
            SOLAR_DOWN_COUNTER = SOLAR_DOWN_COUNTER - 1
        else:
            SOLAR_DOWN_COUNTER = 0
        if SOLAR_DOWN_COUNTER == 0:
            SOLAR_OK = False
            SOLAR_OK_COUNTER = 0
        if SOLAR_DOWN_COUNTER > 0:
            SOLAR_OK = True
     
    if (SOLAR_OK or SALDERING_ON) and heater_switch.value() == 0: heater_switch.on()
    if not (SOLAR_OK or SALDERING_ON) and heater_switch.value() == 1: heater_switch.off()
    
    if DEBUG:
        print("Heating, SOLAR_OK_COUNTER", onoff, SOLAR_OK_COUNTER)
        print("Read temp", temp)
        print("last p1 message", last_p1_message)
        print("RSSI", str(wlan.status('rssi')))
#        print("%x"%roms[0])
#        print("".join("{:02x}-".format(x) for x in roms[0]))
        print("last prod:%d, temp: %0.1f, solar OK: %d, heat on/off: %d" % (int(last_production_value), temp, SOLAR_OK, onoff))
        print("last p1 time", p1_timestamp)
    blinkN(1,led)
