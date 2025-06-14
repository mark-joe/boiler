from machine import Pin
import onewire
import ds18x20
import time

p = Pin(15, Pin.IN, Pin.PULL_UP)
ow = onewire.OneWire(p)
ds = ds18x20.DS18X20(ow)
roms = ds.scan()
print(roms)
while True:
    ds.convert_temp()
    v = ds.read_temp(roms[0])
    print("%.1f" % v)
    time.sleep(1)
