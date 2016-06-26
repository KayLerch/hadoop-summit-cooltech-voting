#!/usr/bin/env python3
import getopt
import ssl
import uuid
import sys
import paho.mqtt.client as mqtt
import Adafruit_DHT
import logging
from logging.handlers import RotatingFileHandler

sensor = Adafruit_DHT.DHT22

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logFile = "./logs/temperature.log"

# comes from outside as arguments
thingName = ""
mqttTopic_pub = ""
sensorPin = "21"
mqttEndpoint = ""  # something like A1B71MLXKNXXXX.iot.us-east-1.amazonaws.com

mqttCert_Protocol = ssl.PROTOCOL_TLSv1_2
mqttCert_ca = "./cert/VeriSign-Class-3-Public-Primary-Certification-Authority-G5.pem"
mqttPort = 8883
mqttClientId = "consumer-" + str(uuid.uuid4())
mqttClient = mqtt.Client(client_id=mqttClientId, clean_session=True)

# called while client tries to establish connection with the server
def on_connect(mqttc, obj, flags, rc):
    if rc == 0:
        global mqttClientConnCount
        logger.info("Client " + mqttClientId + " conntected : " + str(rc) + " | Connection status: successful.")
        # initial publication of temperature and humidty
        publish_data()


def on_disconnect(client, userdata, rc):
    logger.info("Client connection closed.")


def teardown():
    mqttClient.disconnect()
    mqttClient.loop_stop()
    sys.exit()


def on_publish(mosq, obj, mid):
    publish_data()


def on_log(pahoClient, obj, level, string):
    logger.debug(string)


def addFileLogger():
    global logger
    handler = RotatingFileHandler(logFile, maxBytes=1024*1024*10,backupCount=3)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


def addConsoleLogger():
    global logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

def publish_data():
    humidity, temperature = Adafruit_DHT.read_retry(sensor, int(sensorPin))
    if humidity is not None and temperature is not None:
        payload = '{{"state":{{"reported":{{"humidity":{0:0.1f},"temperature":{1:0.1f}}}}}}}' \
            .format(humidity,celsiusToFahrenheit(temperature))
        logger.info("Publish {0} to {1}".format(payload, mqttTopic_pub))
        mqttClient.publish(mqttTopic_pub, payload, 0, False)


def celsiusToFahrenheit(temperature):
    return (temperature * (9/5)) + 32


def connect_mqtt():
    mqttCert = "./cert/" + thingName + "/certificate.pem.crt"
    mqttCert_priv = "./cert/" + thingName + "/private.pem.key"
    # subsribe callback methods to mqtt-events
    mqttClient.on_connect = on_connect
    mqttClient.on_publish = on_publish
    mqttClient.on_disconnect = on_disconnect
    mqttClient.on_log = on_log

    # Configure network encryption and authentication options. Enables SSL/TLS support.
    # adding client-side certificates and enabling tlsv1.2 support as required by aws-iot service
    mqttClient.tls_set(mqttCert_ca, certfile=mqttCert, keyfile=mqttCert_priv, tls_version=mqttCert_Protocol, ciphers=None)

    logger.info("Start connecting to " + mqttEndpoint + ":" + str(mqttPort) + " ...")

    try:
        # connecting to aws-account-specific iot-endpoint
        mqttClient.connect(mqttEndpoint, port=mqttPort)
        mqttClient.loop_forever()
    except (KeyboardInterrupt, SystemExit):
        teardown()


def main(argv):
    opts, args = getopt.getopt(argv, "vt:p:e:", ["thing=","pin=","endpoint=","verbose"])
    global thingName
    global mqttTopic_pub
    global sensorPin
    global mqttEndpoint

    addFileLogger()

    for opt, arg in opts:
        if opt in ('-t', '--thing'):
            thingName = arg
            mqttTopic_pub = "$aws/things/" + thingName + "/shadow/update"
        elif opt in ('-p', '--pin'):
            sensorPin = arg
        elif opt in ('-e', '--endpoint'):
            mqttEndpoint = arg
        elif opt in ('-v', '--verbose'):
            addConsoleLogger()

    if not thingName:
        logger.error("No thing set. Provide a thing registered in AWS IoT to report air condition to with -t or --thing argument.")
    elif not sensorPin:
        logger.error("No GPIO pin set. Provide a GPIO pin which is connect to DHT22 temperature sensor with -p or --pin argument.")
    elif not mqttEndpoint:
        logger.error("No MQTT endpoint set. Provide an endpoint address to AWS IoT with -e or --endpoint argument. And endpoint is expected to look like A1B71MLXKNXXXX.iot.us-east-1.amazonaws.com")
    else:
        connect_mqtt()

if __name__ == "__main__":
    main(sys.argv[1:])