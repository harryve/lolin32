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

#print("\n\n\n")
#print("start\n")

hostname = "mobsens"

try:
    temp, hum = read_sensor()
    print("Temperature: %0.2f C" % temp)
    print("Humidity: %0.2f %%" % hum)

    vbat = read_vbat()
    print("Vbat: %0.2f V" % vbat)

    #print("Init done, start network")
    t_start = time.ticks_ms()

    wlan = network.WLAN(network.STA_IF) 
    wlan.ifconfig(('192.168.62.4', '255.255.255.0', '192.168.62.1', '192.168.62.5'))
    wlan.active(True)
    wlan.config(dhcp_hostname = hostname)
    wlan.connect('Harrys Wlan', 'Hallo, weer Harry1 dus')

    #print("Wait while connected")
    timo = 50
    while not wlan.isconnected() and timo > 0:
        time.sleep(.1)
        timo -= 1
    if timo <= 0:
        raise Exception("Cannot connect to network")

    t_nwk_connected = time.ticks_ms()

    print("Connection successful", wlan.status('rssi'), t_nwk_connected)

    mqtt_server = 'mqtt.harry.thuis'
    #mqtt_server = '192.168.62.99'
    #print("Connect to mqtt broker")
    client = MQTTClient("umqtt_client", mqtt_server)

    client.connect()
    #print("Connected")
    msg = {
        "temp": float("%0.1f" % temp),
        "hum": int("%.0f" % hum),
        "vbat": float("%0.2f" % vbat),
        "rssi": wlan.status('rssi'),
        "t_start": t_start,
        "t_nwk": t_nwk_connected,
        "t_mqtt": time.ticks_ms() }
    client.publish("tele/%s/sensor" % hostname, json.dumps(msg, separators=(',', ':')), qos=1)

    msg = {
        "t_end": time.ticks_ms()
    }
    client.publish("tele/%s/debug" % hostname, json.dumps(msg, separators=(',', ':')), qos=1)
    client.disconnect()
except Exception as e:
    print(e)

#print("Welterusten")        
machine.deepsleep(60000)
