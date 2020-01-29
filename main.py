from umqtt.simple import MQTTClient
import machine
from machine import Pin, I2C, ADC
from bme280_int import BME280
import network
import utime
import esp


def blink(times=1):
    led = Pin(2, Pin.OUT)
    for _ in range(times):
        led.off()
        utime.sleep_ms(100)
        led.on()
        utime.sleep_ms(200)

blink(1)

def network_wait():
    nic = network.WLAN(network.STA_IF)
    nic.active(True)
    if not nic.isconnected():
        nic.connect()
        counter = 0
        print("Waiting for connection...")
        while not nic.isconnected():
            counter += 1
            utime.sleep(1)
            if counter == 10:
                blink(6)
                machine.reset()

    print(nic.ifconfig())


def report_sensors():
    i2c = I2C(scl=Pin(5), sda=Pin(4), freq=10000)
    bme = BME280(i2c=i2c)

    (temp, pressure, humidity) = bme.read_compensated_data()

    CLIENT_ID = "cripple"
    mqtt = MQTTClient(CLIENT_ID, 'libreelec.lan')
    mqtt.connect()
    mqtt.publish(
        'global/house/temperature/{}'.format(CLIENT_ID), str(temp/100))
    print('temp: {}'.format(temp/100))
    mqtt.publish('global/house/pressure/{}'.format(CLIENT_ID),
                 str(pressure/25600))
    print('pres: {}'.format(pressure/25600))
    mqtt.publish('global/house/humidity/{}'.format(CLIENT_ID),
                 str(humidity/1024))
    print('humi: {}'.format(humidity/1024))

    adc = ADC(0)
    volts_reading = adc.read()
    volts = volts_reading/241.0
    mqtt.publish('global/voltage/{}'.format(CLIENT_ID), str(volts))
    print('volt: {}'.format(volts))

    mqtt.disconnect()


def set_sleep(sleep):
    rtc = machine.RTC()
    mem = b'{}'.format(sleep)
    rtc.memory(mem)


def go_to_sleep(force=True):
    if force or machine.reset_cause() == machine.DEEPSLEEP_RESET or machine.reset_cause() == machine.WDT_RESET:
        rtc = machine.RTC()
        # that's in microseconds
        sleep = 10*60*1000*1000
        mem = rtc.memory()
        if mem != b'':
            sleep = int(mem)

        esp.deepsleep(sleep)


blink(2)
network_wait()
blink(3)
report_sensors()
blink(4)
go_to_sleep(False)
