import machine
import time
import network
import json
import bme280
import persist
import cred

from mqttsimple import MQTTClient

def read_sensor():
    i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
    sensor = bme280.BME280(i2c=i2c)
    temperature = sensor.temperature
    humidity = sensor.humidity
    pressure = sensor.pressure
    return temperature, humidity, pressure

def read_vbat():
    vbat_adc = machine.ADC(machine.Pin(35))
    vbat_adc.atten(machine.ADC.ATTN_11DB)       #Full range: 3.3v
    return (vbat_adc.read_uv() * 2) / 1000000.0

hostname = "mobsens"

try:
    t_start = time.ticks_ms()
    temp, hum, pres = read_sensor()
    #print("Temperature: %0.2f C" % temp)
    #print("Humidity: %0.2f %%" % hum)
    #print("Pres: %0.1f hPa" % pres)

    vbat = read_vbat()
    #print("Vbat: %0.2f V" % vbat)

    pers = persist.Persist()
    start_count = pers.get_counter()
    pers.set_counter(pers.get_counter() + 1)

    wlan = network.WLAN(network.STA_IF) 
    wlan.ifconfig(('192.168.62.4', '255.255.255.0', '192.168.62.1', '192.168.62.5'))
    wlan.active(True)
    wlan.config(dhcp_hostname = hostname)
    wlan.connect(cred.NETWORK, cred.PW)

    #print("Wait while connected")
    timo = 50
    while not wlan.isconnected() and timo > 0:
        time.sleep(.1)
        timo -= 1
    if timo <= 0:
        raise Exception("Cannot connect to network")

    #print("Connection successful. RSSI = {0}".format(wlan.status('rssi')))

    client = MQTTClient("mobsens", 'mqtt.harry.thuis')
    client.connect()
    #print("MQTT connected")
    msg = {
        "temp": float("%0.1f" % temp),
        "hum": int("%.0f" % hum),
        "pressure": float("%.1f" % pres),
        "vbat": float("%0.2f" % vbat),
        "rssi": wlan.status('rssi'),
        "runtime": pers.get_prev_runtime(),
        "counter": start_count }
    print(msg)
    client.publish("tele/%s/sensor" % hostname, json.dumps(msg, separators=(',', ':')), qos=1)
    client.disconnect()

    t_end = time.ticks_ms()
    pers.set_prev_runtime(t_end - t_start)

except Exception as e:
    print(e)

#print("Welterusten")

machine.deepsleep(5*60000)
