from umqtt.simple import MQTTClient
import machine
from machine import Pin, I2C, ADC
from bme280_int import BME280
import network
import utime
import esp
import usyslog
import ntptime
import time
import webrepl
import json

client_id = 'cripple'

class PrintClient(usyslog.SyslogClient):
    def __init__(self):
        super().__init__()

    def log(self, severity, msg):
        data = "<%d>%s" % (severity + (self._facility << 3), msg)
        print(data)
        
    def close(self):
        pass



class CombineClient(usyslog.SyslogClient):
    def __init__(self, loggers):
        self.loggers = loggers
        super().__init__()

    def log(self, severity, msg):
        for log in self.loggers:
            log.log(severity, msg)

    def close(self):
        pass



log = PrintClient()


def blink(times=1):
    led = Pin(2, Pin.OUT)
    for _ in range(times):
        led.off()
        utime.sleep_ms(100)
        led.on()
        utime.sleep_ms(200)



blink(1)



def init_network():
    nic = network.WLAN(network.STA_IF)
    nic.active(True)
    if not nic.isconnected():
        nic.connect()
        print("Waiting for connection...")
        while not nic.isconnected():
            utime.sleep(1)

    print(nic.ifconfig())
    global client_id
    client_id = nic.config('dhcp_hostname')



def get_logger():
    global log
    log = CombineClient([usyslog.UDPClient('nas.lan'), PrintClient()])



def connect_mqtt():
    mqtt = MQTTClient(client_id, 'nas.lan', keepalive=60)
    mqtt.set_last_will('{}/state'.format(client_id), 'offline', retain=True)
    mqtt.connect()
    log.info('MQTT connected')

    mqtt.publish(
        '{}/state'.format(client_id),
        'online', retain=False)

    return mqtt



def publish_config(mqtt):
    device = {
        "manufacturer": "bilbas",
        "model": "esp8266-bme280",
        "identifiers": [
            client_id
        ]
    }

    temp_topic = 'homeassistant/sensor/{}/temperature/config'.format(client_id)
    temp_config = {
        "device": device,
        "~": client_id,
        "unique_id": "{}_temp".format(client_id),
        "device_class": "temperature",
        "name": "Temperature",
        "state_topic": "~/temperature",
        "unit_of_measurement": "°C"
    }

    mqtt.publish(
        temp_topic,
        json.dumps(temp_config), retain=True)


    pressure_topic = 'homeassistant/sensor/{}/pressure/config'.format(
        client_id)
    pressure_config = {
        "device": device,
        "~": client_id,
        "unique_id": "{}_pressure".format(client_id),
        "device_class": "pressure",
        "name": "Pressure",
        "state_topic": "~/pressure",
        "unit_of_measurement": "hPa",
        "availability_topic": "~/state"
    }

    mqtt.publish(
        pressure_topic,
        json.dumps(pressure_config), retain=True)


    humidity_topic = 'homeassistant/sensor/{}/humidity/config'.format(
        client_id)
    humidity_config = {
        "device": device,
        "~": client_id,
        "unique_id": "{}_humidity".format(client_id),
        "device_class": "humidity",
        "name": "Humidity",
        "state_topic": "~/humidity",
        "unit_of_measurement": "%",
        "availability_topic": "~/state"
    }

    mqtt.publish(
        humidity_topic,
        json.dumps(humidity_config), retain=True)


    battery_topic = 'homeassistant/sensor/{}/battery/config'.format(client_id)
    battery_config = {
        "device": device,
        "~": client_id,
        "unique_id": "{}_voltage".format(client_id),
        "device_class": "battery",
        "name": "Battery",
        "state_topic": "~/voltage",
        "unit_of_measurement": "V",
        "availability_topic": "~/state"
    }

    mqtt.publish(
        battery_topic,
        json.dumps(battery_config), retain=True)



def report_sensors(mqtt):
    i2c = I2C(scl=Pin(5), sda=Pin(4), freq=10000)
    bme = BME280(i2c=i2c)

    (temp, pressure, humidity) = bme.read_compensated_data()

    mqtt.publish(
        '{}/temperature'.format(client_id),
        str(temp/100), retain=False)
    log.info('temp: {}'.format(temp/100))

    mqtt.publish(
        '{}/pressure'.format(client_id),
        str(pressure/25600), retain=False)
    log.info('pres: {}'.format(pressure/25600))

    mqtt.publish(
        '{}/humidity'.format(client_id),
        str(humidity/1024), retain=False)
    log.info('humi: {}'.format(humidity/1024))

    adc = ADC(0)
    volts_reading = adc.read()
    volts = volts_reading/239.0

    mqtt.publish(
        '{}/voltage'.format(client_id), str(volts), retain=False)
    log.info('volt: {}'.format(volts))

    mqtt.publish(
        '{}/status'.format(client_id), 'disconnected', retain=True)



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

    if not force and webrepl.client_s:
        log.info('webrepl connected, not going to sleep')
        return

    if force or reset_cause == machine.DEEPSLEEP_RESET or reset_cause == machine.WDT_RESET:
        log.info('going deep sleep')
        esp.deepsleep(sleep)



def main():
    blink(2)
    try:
        init_network()
        get_logger()
        try:
            ntptime.settime()
        except Exception as e:
            log.error("Error: %s" % e)

        localtime = time.localtime()
        log.info('init {}'.format(localtime))

        reset_cause = machine.reset_cause()
        log.info("Reset cause: %s" % reset_cause)
        blink(3)

        mqtt = connect_mqtt()
        publish_config(mqtt)
        report_sensors(mqtt)
        mqtt.disconnect()
        log.info('MQTT disconnected')

        blink(4)
        go_to_sleep(False)
    except Exception as e:
        log.error("Error: %s" % e)



main()
