from umqtt.simple import MQTTClient
import machine
from machine import Pin, I2C, ADC
from bme280_int import BME280
import network
import utime
import esp

def network_wait():
    nic = network.WLAN(network.STA_IF)
    if not nic.isconnected():
        nic.connect()
        print("Waiting for connection...")
        while not nic.isconnected():
            utime.sleep(1)
    print(nic.ifconfig())

def report_sensors():
    i2c = I2C(scl=Pin(5), sda=Pin(4), freq=10000)
    bme = BME280(i2c=i2c)

    (temp, pressure, humidity) = bme.read_compensated_data()

    CLIENT_ID = "cripple"
    mqtt = MQTTClient(CLIENT_ID, 'libreelec.lan')
    mqtt.connect()
    mqtt.publish('global/house/temperature/{}'.format(CLIENT_ID), str(temp/100))
    mqtt.publish('global/house/pressure/{}'.format(CLIENT_ID), str(pressure/25600))
    mqtt.publish('global/house/humidity/{}'.format(CLIENT_ID), str(humidity/1024))

    adc = ADC(0)
    volts_reading = adc.read()
    volts = volts_reading*0.00419
    mqtt.publish('global/voltage/{}'.format(CLIENT_ID), str(volts))

    mqtt.disconnect()

network_wait()
report_sensors()

if (machine.reset_cause() == machine.DEEPSLEEP_RESET):
    # that's in microseconds
    esp.deepsleep(10*60*1000*1000)
