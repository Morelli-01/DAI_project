import socket
import threading
import time
from multiprocessing import Value
from time import sleep
import json
import numpy as np
import paho.mqtt.client as mqtt
import uuid
import signal, sys

WELL_KNOWN = '/.well-known'
ADD_DEVICE_TOPIC = WELL_KNOWN + '/add'
REMOVE_DEVICE_TOPIC = WELL_KNOWN + '/del'


class WorkerMqtt():

    def __init__(self, broker_host='localhost', broker_port=1883, debug=False, id_client=None):
        if id_client == None:
            self.id_client = 'worker-' + str(uuid.uuid4())
        else:
            self.id_client = str(id_client)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.debug = debug
        self.stop_ = True

        self.client_ = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.id_client)
        self.client_.on_connect = self.on_connect
        self.client_.on_message = self.on_message
        self.client_.connect(host=self.broker_host, port=self.broker_port, keepalive=6000)
        self.add_device()
        self.client_.subscribe(topic=f"/{self.id_client}/#")

    def add_device(self):
        msg = {'id': self.id_client}
        self.client_.publish(topic=ADD_DEVICE_TOPIC, qos=2, payload=json.dumps(msg).encode())
        if self.debug_:
            print("Registered to service-dicovery")

    def del_device(self):
        msg = {'id': self.id_client}
        self.client_.publish(topic=REMOVE_DEVICE_TOPIC, payload=json.dumps(msg).encode())
        self.client_.loop_read()
        self.client_.loop_write()
        if self.debug_:
            print("Removed from service-dicovery")

    def on_message(self, client, userdata, msg):
        decoded_msg = json.loads(msg.decode())
        if self.debug:
            print(f"{self.id_client} Received message from topic {msg.topic}:\n msg.payload: {msg.payload} ")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if self.debug:
            print(f"{self.id_client} has connected with result code {reason_code}")

    def stop(self):
        self.stop_ = True
        self.del_device()
        self.client_.loop_read()
        self.client_.loop_write()
        self.client_.disconnect()

    def run(self):
        self.stop_ = False
        while not self.stop_:
            self.client_.loop_read()
            self.client_.loop_write()


def handle_sigint(signal_number, frame):
    worker.stop()
    print("Worker correctly stopped")
    sys.exit(signal_number)


signal.signal(signal.SIGINT, handle_sigint)
global worker
worker = WorkerMqtt(debug=True)
worker.run()
