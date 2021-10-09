from umqtt.simple import MQTTClient
import machine
from machine import Pin, I2C, ADC
from bme280_int import BME280
import network
import utime
import esp
import socket
import usyslog
import sys

CLIENT_ID = 'cripple'

log = usyslog.SyslogClient()

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


def get_logger():
    global log
    log = usyslog.UDPClient('libreelec.lan')
    return log


def report_sensors():
    i2c = I2C(scl=Pin(5), sda=Pin(4), freq=10000)
    bme = BME280(i2c=i2c)

    (temp, pressure, humidity) = bme.read_compensated_data()

    mqtt = MQTTClient(CLIENT_ID, 'libreelec.lan', keepalive=60)
    mqtt.set_last_will('{}/status'.format(CLIENT_ID), 'offline', retain = True)
    mqtt.connect()
    log.info('MQTT connected')

    mqtt.publish(
        '{}/status'.format(CLIENT_ID),
        'connected', retain = True)

    mqtt.publish(
        '{}/temperature'.format(CLIENT_ID),
        str(temp/100), retain = True)
    log.info('temp: {}'.format(temp/100))

    mqtt.publish(
        '{}/pressure'.format(CLIENT_ID),
        str(pressure/25600), retain = True)
    log.info('pres: {}'.format(pressure/25600))

    mqtt.publish(
        '{}/humidity'.format(CLIENT_ID),
        str(humidity/1024), retain = True)
    log.info('humi: {}'.format(humidity/1024))

    adc = ADC(0)
    volts_reading = adc.read()
    volts = volts_reading/239.0

    mqtt.publish(
        '{}/voltage'.format(CLIENT_ID), str(volts), retain = True)
    log.info('volt: {}'.format(volts))

    mqtt.publish(
        '{}/status'.format(CLIENT_ID), 'disconnected', retain = True)

    mqtt.disconnect()
    log.info('MQTT disconnected')


def set_sleep(sleep):
    rtc = machine.RTC()
    mem = b'{}'.format(sleep)
    rtc.memory(mem)


def go_to_sleep(force=True):
    log.info('go_to_sleep({})'.format(force))
    reset_cause = machine.reset_cause()
    log.info('That was a reset #{}'.format(reset_cause))

    rtc = machine.RTC()
    log.info('rtc created')
    # that's in microseconds
    sleep = 10*60*1000*1000
    mem = rtc.memory()
    log.info('rtc memory read')
    if mem != b'':
        log.info('mem is {}'.format(mem))
        sleep = int(mem)

    if force or reset_cause == machine.DEEPSLEEP_RESET or reset_cause == machine.WDT_RESET:
        log.info('going deep sleep')
        esp.deepsleep(sleep)

def main():
    blink(2)
    network_wait()
    try:
        get_logger()
        reset_cause = machine.reset_cause()
        log.info("Reset cause: %s" % reset_cause)
        blink(3)
        report_sensors()
        blink(4)
        go_to_sleep(False)
    except Exception as e:
        log.error("Error: %s" % e)
    finally:
        log.close()

main()
