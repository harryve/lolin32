#from machine import Pin, I2C, ADC
import machine
import time
import network
import ahtx0
#import ubinascii
import json

from mqttsimple import MQTTClient

print("\n\n\n")
print("start\n")

#led = machine.Pin(5, machine.Pin.OUT)
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
sensor = ahtx0.AHT10(i2c)

vbat = machine.ADC(machine.Pin(35))
vbat.atten(machine.ADC.ATTN_11DB)       #Full range: 3.3v

print("Init done, start network")
t_start = time.ticks_ms()

wlan = network.WLAN(network.STA_IF) # create station interface
wlan.active(True)       # activate the interface
#print(wlan.scan())             # scan for access points
wlan.connect('Harrys Wlan', 'Hallo, weer Harry1 dus') # connect to an AP

print("Wait while connected")
timo = 50
while not wlan.isconnected() and timo > 0:
    time.sleep(.1)
    timo -= 1
if timo <= 0:
    print("Cannot connect to network")
    machine.deepsleep(60000)

t_nwk_connected = time.ticks_ms()

print("Connection successful")
#print(wlan.ifconfig())

#mqtt_server = 'mqtt.harry.thuis'
mqtt_server = '192.168.62.99'
print("Connect to mqtt broker")
client = MQTTClient("umqtt_client", mqtt_server)

#led.value(not led.value())
print("\n")
print("Temperature: %0.2f C" % sensor.temperature)
print("Humidity: %0.2f %%" % sensor.relative_humidity)
vbat_value = (vbat.read_uv() * 2) / 1000000.0
print("Vbatt: %0.2f %%" % vbat_value)

client.connect()
t_mqtt_connected = time.ticks_ms()
msg = "T=%0.2f C, H=%0.2f%%, V=%0.2f, %d %d %d" % (sensor.temperature, sensor.relative_humidity, vbat_value, t_start, t_nwk_connected, t_mqtt_connected)
print("Connected, send message; " + msg)
print("%d %d %d" % (t_start, t_nwk_connected, t_mqtt_connected))
client.publish(b"mobsens", msg, qos=1)
t_end = time.ticks_ms()
msg = "End=%d" % t_end
client.publish(b"mobsens", msg, qos=1)
print("%d" % (t_end))
client.disconnect()
#time.sleep(1)
machine.deepsleep(60000)
