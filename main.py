import machine
import time
import network
import ahtx0
import json

from mqttsimple import MQTTClient

def read_sensor():
    i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
    sensor = ahtx0.AHT10(i2c)
    return sensor.temperature, sensor.relative_humidity

def read_vbat():
    vbat_adc = machine.ADC(machine.Pin(35))
    vbat_adc.atten(machine.ADC.ATTN_11DB)       #Full range: 3.3v
    return (vbat_adc.read_uv() * 2) / 1000000.0

print("\n\n\n")
print("start\n")

try:
    temp, hum = read_sensor()
    print("Temperature: %0.2f C" % temp)
    print("Humidity: %0.2f %%" % hum)

    vbat = read_vbat()
    print("Vbat: %0.2f %%" % vbat)

    print("Init done, start network")
    t_start = time.ticks_ms()

    wlan = network.WLAN(network.STA_IF) 
    wlan.active(True)
    wlan.config(dhcp_hostname = "mobsens")
    wlan.connect('Harrys Wlan', 'Hallo, weer Harry1 dus')

    print("Wait while connected")
    timo = 50
    while not wlan.isconnected() and timo > 0:
        time.sleep(.1)
        timo -= 1
    if timo <= 0:
        raise Exception("Cannot connect to network")

    t_nwk_connected = time.ticks_ms()

    print("Connection successful")

    mqtt_server = 'mqtt.harry.thuis'
    #mqtt_server = '192.168.62.99'
    print("Connect to mqtt broker")
    client = MQTTClient("umqtt_client", mqtt_server)

    client.connect()
    t_mqtt_connected = time.ticks_ms()
    msg = "T=%0.2f C, H=%0.2f%%, V=%0.2f, %d %d %d" % (temp, hum, vbat, t_start, t_nwk_connected, t_mqtt_connected)
    print("Connected, send message; " + msg)
    print("%d %d %d" % (t_start, t_nwk_connected, t_mqtt_connected))
    client.publish(b"mobsens", msg, qos=1)
    t_end = time.ticks_ms()
    msg = "End=%d" % t_end
    client.publish(b"mobsens", msg, qos=1)
    print("%d" % (t_end))
    client.disconnect()
    #time.sleep(1)
except Exception as e:
    print(e)

print("Welterusten")        
machine.deepsleep(60000)
