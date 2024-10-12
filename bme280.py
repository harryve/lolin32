# Authors: Paul Cunnane 2016, Peter Dahlebrg 2016
#
# This module borrows from the Adafruit BME280 Python library. Original
# Copyright notices are reproduced below.
#
# Those libraries were written for the Raspberry Pi. This modification is
# intended for the MicroPython and esp8266 boards.
#
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Based on the BMP280 driver with BME280 changes provided by
# David J Taylor, Edinburgh (www.satsignal.eu)
#
# Based on Adafruit_I2C.py created by Kevin Townsend.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Aangepast en ontkeverd door Harry 

import machine		# To run this script directly
import time
from ustruct import unpack, unpack_from
from array import array
from math import *

# BME280 default address.
BME280_I2CADDR = 0x76

# Operating Mode
BME280_OSAMPLE_1 = 1

# BME280 registers
BME280_REGISTER_CONTROL_HUM = 0xF2
BME280_REGISTER_CONTROL = 0xF4
BME280_REGISTER_CONFIG = 0xf5

class BME280:

    def __init__(self, i2c):
        self.i2c = i2c
        self._mode = BME280_OSAMPLE_1
        self.address = BME280_I2CADDR

        # load calibration data
        dig_88_a1 = self.i2c.readfrom_mem(self.address, 0x88, 26)
        dig_e1_e7 = self.i2c.readfrom_mem(self.address, 0xE1, 7)
        self.dig_T1, self.dig_T2, self.dig_T3, self.dig_P1, \
            self.dig_P2, self.dig_P3, self.dig_P4, self.dig_P5, \
            self.dig_P6, self.dig_P7, self.dig_P8, self.dig_P9, \
            _, self.dig_H1 = unpack("<HhhHhhhhhhhhBB", dig_88_a1)

        self.dig_H2, self.dig_H3 = unpack("<hB", dig_e1_e7)
        e4_sign = unpack_from("<b", dig_e1_e7, 3)[0]
        self.dig_H4 = (e4_sign << 4) | (dig_e1_e7[4] & 0xF)

        e6_sign = unpack_from("<b", dig_e1_e7, 5)[0]
        self.dig_H5 = (e6_sign << 4) | (dig_e1_e7[4] >> 4)
        self.dig_H6 = unpack_from("<b", dig_e1_e7, 6)[0]
        
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL, bytearray([0]))   # Sleep mode

    def read_raw_data(self): #, result):
        """ Reads the raw (uncompensated) data from the sensor.

            Args:
                result: array of length 3 or alike where the result will be
                stored, in temperature, pressure, humidity order
            Returns:
                None
        """
        regval = bytearray(1)
        regval[0] = self._mode
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL_HUM, regval) #self._l1_barray)
        regval[0] = self._mode << 5 | self._mode << 2 | 1           # Forced mode
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL, regval) #self._l1_barray)

        # Calculate the worst case measurement time
        sleep_time = 1250 + 2300 * (1 << self._mode)                # Temperature
        sleep_time = sleep_time + 2300 * (1 << self._mode) + 575    # Pressure
        sleep_time = sleep_time + 2300 * (1 << self._mode) + 575    # Humidity
        time.sleep_us(sleep_time)  # Wait the required time

        # burst readout from 0xF7 to 0xFE, recommended by datasheet
        readout = bytearray(8)
        self.i2c.readfrom_mem_into(self.address, 0xF7, readout)
        raw_press = ((readout[0] << 16) | (readout[1] << 8) | readout[2]) >> 4
        raw_temp = ((readout[3] << 16) | (readout[4] << 8) | readout[5]) >> 4
        raw_hum = (readout[6] << 8) | readout[7]
        return raw_temp, raw_press, raw_hum
    
    def read_compensated_data(self):
        """ Reads the data from the sensor and returns the compensated data.

             Returns:
                Tuple with temperature, pressure, humidity
        """
        raw_temp, raw_press, raw_hum = self.read_raw_data()
        # temperature
        var1 = ((raw_temp >> 3) - (self.dig_T1 << 1)) * self.dig_T2 >> 11
        var2 = (((((raw_temp >> 4) - self.dig_T1) *
                  ((raw_temp >> 4) - self.dig_T1)) >> 12) * self.dig_T3) >> 14
        t_fine = var1 + var2
        temp = (t_fine * 5 + 128) >> 8

        # pressure
        var1 = t_fine - 128000
        var2 = var1 * var1 * self.dig_P6
        var2 = var2 + ((var1 * self.dig_P5) << 17)
        var2 = var2 + (self.dig_P4 << 35)
        var1 = (((var1 * var1 * self.dig_P3) >> 8) +
                ((var1 * self.dig_P2) << 12))
        var1 = (((1 << 47) + var1) * self.dig_P1) >> 33
        if var1 == 0:
            pressure = 0
        else:
            p = 1048576 - raw_press
            p = (((p << 31) - var2) * 3125) // var1
            var1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
            var2 = (self.dig_P8 * p) >> 19
            pressure = ((p + var1 + var2) >> 8) + (self.dig_P7 << 4)

        # humidity
        h = t_fine - 76800
        h = (((((raw_hum << 14) - (self.dig_H4 << 20) -
                (self.dig_H5 * h)) + 16384)
              >> 15) * (((((((h * self.dig_H6) >> 10) *
                            (((h * self.dig_H3) >> 11) + 32768)) >> 10) +
                          2097152) * self.dig_H2 + 8192) >> 14))
        h = h - (((((h >> 15) * (h >> 15)) >> 7) * self.dig_H1) >> 4)
        h = 0 if h < 0 else h
        h = 419430400 if h > 419430400 else h
        humidity = h >> 12

        return temp, pressure, humidity

    @property
    def values(self):
        """ human readable values """

        t, p, h = self.read_compensated_data()

        pa = p // 256
        pi = pa // 100
        pd = pa - pi * 100

        hi = h // 1024
        hd = h * 100 // 1024 - hi * 100
        #print("{}C".format(t / 100), "{}.{:02d}%".format(hi, hd), "{}.{:02d}hPa".format(pi, pd))
    
        return t / 100, h / 1024 , p / 25600.0

if __name__ == "__main__":
    i2c = machine.I2C(scl=machine.Pin(13), sda=machine.Pin(12))
    sensor = BME280(i2c=i2c)
    while True:
        print(sensor.values)
        time.sleep(5)
