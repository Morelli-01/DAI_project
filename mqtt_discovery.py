import socket
import threading
import time
from dis import disco
from multiprocessing import Value
from time import sleep
import json
import numpy as np
import paho.mqtt.client as mqtt
import uuid, signal, sys

WELL_KNOWN = '/.well-known'
ADD_DEVICE_TOPIC = WELL_KNOWN + '/add'
REMOVE_DEVICE_TOPIC = WELL_KNOWN + '/del'


class MqttDiscovery():

    def __init__(self, broker_host='localhost', broker_port=1883, debug=True, id_client=None):
        if id_client == None:
            self.id_client = "discovery-service-" + str(uuid.uuid4())
        else:
            self.id_client = str(id_client)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.devices_ = []
        self.debug = debug
        self.stop_ = True
        self.client_ = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.id_client)
        self.client_.on_connect = self.on_connect
        self.client_.on_message = self.on_message
        self.client_.connect(host=self.broker_host, port=self.broker_port, keepalive=6000)
        self.client_.subscribe(topic=f"{WELL_KNOWN}/#")

    def on_message(self, client, userdata, msg):
        decoded_msg = json.loads(msg.payload.decode())
        if self.debug:
            print(f"{self.id_client} Received message from topic {msg.topic}:\n {msg.payload} ")

        if msg.topic == WELL_KNOWN and msg.retain:
            self.devices_ = decoded_msg['ids']

        if msg.topic == ADD_DEVICE_TOPIC:
            self.devices_.append(decoded_msg['id'])
            self.topic_update()

        if msg.topic == REMOVE_DEVICE_TOPIC:
            self.devices_.remove(decoded_msg['id'])
            self.topic_update()

    def topic_update(self):
        self.client_.publish(topic=WELL_KNOWN, payload=json.dumps({'ids': self.devices_}).encode(), qos=2, retain=True)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if self.debug:
            print(f"{self.id_client} has connected with result code {reason_code}")

    def stop(self):
        self.stop_ = True
        self.client_.disconnect()

    def run(self):
        self.stop_ = False
        while not self.stop_:
            self.client_.loop_read()
            self.client_.loop_write()


def handle_sigint(signal_number, frame):
    discovery_service.stop()
    print("Worker correctly stopped")
    sys.exit(signal_number)


signal.signal(signal.SIGINT, handle_sigint)
global discovery_service
discovery_service = MqttDiscovery(debug=True)
discovery_service.run()
