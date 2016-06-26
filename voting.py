#!/usr/bin/env python3
import getopt
import ssl
import uuid
import json
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import paho.mqtt.client as mqtt
from rgbmatrix import RGBMatrix
from rgbmatrix import graphics

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logFile = "./logs/voting.log"

# configuration which comes with command arguments
thingName = ""
mqttTopic_sub = ""
mqttEndpoint = "" # something like A1B71MLXKNXXXX.iot.us-east-1.amazonaws.com"

# mqtt related config
mqttCert_Protocol = ssl.PROTOCOL_TLSv1_2
mqttCert_ca = "./cert/VeriSign-Class-3-Public-Primary-Certification-Authority-G5.pem"
mqttPort = 8883
mqttClientId = "consumer-" + str(uuid.uuid4())
mqttClient = mqtt.Client(client_id=mqttClientId, clean_session=True)

# rgbmatrix related config
myMatrix = RGBMatrix(32, 1, 1)

fontLarge = graphics.Font()
fontLarge.LoadFont("./fonts/10x20.bdf".encode("utf-8"))

fontSmall = graphics.Font()
fontSmall.LoadFont("./fonts/4x6.bdf".encode("utf-8"))

white = graphics.Color(255, 255, 255)
lightYellow = graphics.Color(255, 255, 153)

# this is the counter for incoming messages
count = 0

# called while client tries to establish connection with the server
def on_connect(mqttc, obj, flags, rc):
    if rc == 0:
        global mqttClientConnCount
        logger.info("Client " + mqttClientId + " conntected : " + str(rc) + " | Connection status: successful.")
        # subscribe to topic to receive votes
        mqttClient.subscribe(mqttTopic_sub, 1)


def on_disconnect(client, userdata, rc):
    logger.info("Client connection closed.")


def on_subscribe(mqttc, obj, mid, granted_qos):
    logger.info("Topic subscribed : " + str(mid) + " " + str(granted_qos) + "data" + str(obj))


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


def teardown():
    myMatrix.Clear()
    mqttClient.unsubscribe(mqttTopic_sub)
    mqttClient.disconnect()
    mqttClient.loop_stop()
    sys.exit()


def work_on_message(payload):
    # extract progress from json payload
    payloadJson = json.loads(payload)
    if "state" not in payloadJson:
        logger.warn("Payload does not contain state-object.")
        return
    payloadState = payloadJson["state"]

    if "desired" not in payloadState:
        logger.warn("state does not contain desired-object.")
        return
    payloadDesired = payloadState["desired"]

    if "voteFromTwilio" in payloadDesired and payloadDesired["voteFromTwilio"]:
        displayNumber(153,0,0) # display with red flash
    else:
        displayNumber(0,153,0) # display with green flash


def displayNumber(r, g, b):
    myMatrix.Fill(r,g,b)
    drawNumber(count)

    time.sleep(0.035)

    myMatrix.Clear()
    drawNumber(count)


def drawNumber(num):
    numstr = str(num)
    width = 1
    if len(numstr) == 1 : width = 12;
    if len(numstr) == 2 : width = 7;
    if len(numstr) == 4 : width = -9;
    graphics.DrawText(myMatrix, fontLarge, width, 21, white, numstr.encode("utf-8"))

    fullThousand = num / 1000
    if fullThousand >= 1:
        while fullThousand > 0:
            graphics.DrawText(myMatrix, fontSmall, 1 + (3 * (fullThousand - 1)), 6, lightYellow, "|".encode("utf-8"))
            fullThousand = fullThousand - 1


def on_message(mqttc, obj, msg):
    global count
    count = count + 1
    payload = str(msg.payload).replace("b'", "", 1).replace("'", "")
    logger.info("Message received (" + str(count)+ ") : " + msg.topic + " : " + payload)
    work_on_message(payload)


def connect_mqtt():
    mqttCert = "./cert/" + thingName + "/certificate.pem.crt"
    mqttCert_priv = "./cert/" + thingName + "/private.pem.key"
    # subsribe callback methods to mqtt-events
    mqttClient.on_connect = on_connect
    mqttClient.on_subscribe = on_subscribe
    mqttClient.on_message = on_message
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
    opts, args = getopt.getopt(argv, "vt:e:", ["thing=","endpoint=","verbose"])
    global thingName
    global mqttTopic_sub
    global mqttEndpoint

    addFileLogger()

    for opt, arg in opts:
        if opt in ('-t', '--thing'):
            thingName = arg
            mqttTopic_sub = "$aws/things/" + thingName + "/shadow/update/delta"
        elif opt in ('-e', '--endpoint'):
            mqttEndpoint = arg
        elif opt in ('-v', '--verbose'):
            addConsoleLogger()

    if not thingName:
        logger.error("No thing set. Provide a thing registered in AWS IoT to report air condition to with -t or --thing argument.")
    elif not mqttEndpoint:
        logger.error("No MQTT endpoint set. Provide an endpoint address to AWS IoT with -e or --endpoint argument. And endpoint is expected to look like A1B71MLXKNXXXX.iot.us-east-1.amazonaws.com")
    else:
        connect_mqtt()

if __name__ == "__main__":
    main(sys.argv[1:])