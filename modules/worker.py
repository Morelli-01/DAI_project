import socket
import threading
import time
from multiprocessing import Value
from time import sleep
import json
import numpy as np
import paho.mqtt.client as mqtt
import uuid

WELL_KNOWN = '/.well-known'


def extract_token(decoded_data):
    return int(decoded_data[decoded_data.find('{') + 1: decoded_data.find('}')])


class Worker():
    def __init__(self, host="localhost", port=None, debug=False, next_host=("", None), shared_var=None):
        super().__init__()
        self.host = host
        self.port = port
        self.name = self.host + ":" + str(self.port)
        self.next_host = next_host
        self.debug_ = debug
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((self.host, self.port))
        self._stop_event = threading.Event()
        self.cycles_counter = 1
        self.shared_var = shared_var
        self.result_available = 0
        self.hook_func = lambda: None
        if self.debug_:
            print("Socket is ready!")
        self.stop_ = False

    def assign_work(self, row: np.ndarray, cols: np.ndarray, proc_index, hook_func=lambda: None):
        self.row = row
        self.cols = cols.T
        self.proc_index = proc_index
        self.work_done = False
        self.hook_func = hook_func

    def token_passing_(self, result=None):
        try:
            prev_conn, prev_addr = self.s.accept()
            self.hook_func()
            data = prev_conn.recv(1024)
            decoded_data = data.decode()
            token_value = extract_token(decoded_data)
            prev_conn.close()

            if self.debug_:
                print(f"{self.name} received: {decoded_data}")

            if self.debug_:
                if bool(self.result_available):
                    print(f"{self.name} is doing some job...")
                else:
                    print('passing token')

            if bool(self.result_available):
                self.shared_var[self.proc_index] = result
                token_value -= 1
                self.result_available -= 1

            if decoded_data.__contains__(self.name):
                self.cycles_counter += 1

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as send_socket:
                send_socket.connect(self.next_host)
                decoded_data = decoded_data[:decoded_data.find('{') + 1] + str(token_value) + decoded_data[
                                                                                              decoded_data.find('}'):]
                data = decoded_data.encode()
                send_socket.sendall(data)

            if token_value == 0:
                self.work_done = True

        except BlockingIOError:
            pass

    def run(self):
        self.s.listen()
        self.s.setblocking(False)
        i = 0
        result = np.zeros((self.cols.shape[0]))
        while not self.work_done:

            self.token_passing_(result=result)

            if i >= result.shape[0]:
                continue
            result[i] = (self.row * self.cols[i]).sum()
            i += 1
            if i >= result.shape[0]:
                self.result_available += 1
                self.s.setblocking(True)

    def stop(self):
        self._stop_event.set()

    def starter(self, token_value):
        self.start()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as send_socket:
            send_socket.connect(self.next_host)
            send_socket.sendall(f"Token {{{token_value}}} from {self.name}".encode())


class MqttWorker(threading.Thread):

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if self.debug_:
            print(f"{self.id} has connected with result code {reason_code}")

    def on_message(self, client, userdata, msg):
        decoded_msg = json.loads(msg.payload.decode())
        if self.debug_:
            print(self.id + ": " + msg.topic + " " + str(msg.payload))

        if msg.topic == WELL_KNOWN:
            decoded_msg = json.loads(msg.payload.decode())
            self.workers_['ids'] = decoded_msg['ids']

        if msg.topic == f"/{self.id}/request":
            self.critical_queue_[float(decoded_msg['timestamp'])] = decoded_msg['id']
            self.client_.publish(topic=f"/{decoded_msg['id']}/response", payload=json.dumps({'id': self.id}).encode())
            print(f"{self.id}: send response to {decoded_msg['id']}")

        if msg.topic == f"/{self.id}/response":
            if not self.confirmation_ids_.__contains__(decoded_msg['id']):
                self.confirmation_ids_.append(decoded_msg['id'])
                print(f"{self.id}: received response from {decoded_msg['id']}")

        if msg.topic == f"/{self.id}/release":
            self.critical_queue_.pop(float(decoded_msg['timestamp']))

    def stop(self):
        self.stop_ = True

    def __init__(self, id=None, broker_host='localhost', broker_port=1883, debug=False, shared_var=None):
        super().__init__()
        if id == None:
            self.id = str(uuid.uuid4())
        else:
            self.id = str(id)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.shared_var = shared_var
        self.debug_ = debug
        self.client_ = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.id)
        self.client_.on_connect = self.on_connect
        self.client_.on_message = self.on_message
        self.client_.connect(host=self.broker_host, port=self.broker_port, keepalive=6000)
        self.stop_ = False
        self.workers_ = {'ids': []}
        self.critical_queue_ = {}
        self.n_confirmation_ = 0
        self.confirmation_ids_ = []
        self.got_access_ = False
        self.work_done = False

        msg = {'id': self.id}
        self.client_.publish(topic=WELL_KNOWN + '/add', payload=json.dumps(msg).encode())
        self.client_.subscribe(topic='/' + self.id + '/#', qos=2)

    def assign_work(self, row: np.ndarray, cols: np.ndarray, proc_index):
        self.row = row
        self.cols = cols.T
        self.proc_index = proc_index
        self.work_done = False

    def lamport_access(self, result):
        self.client_.subscribe(WELL_KNOWN, qos=2)
        while self.workers_['ids'].__len__() == 0:
            self.client_.loop_read()
            self.client_.loop_write()
        self.client_.unsubscribe(WELL_KNOWN)

        request_msg = {
            'id': self.id,
            'timestamp': str(time.time())
        }
        self.critical_queue_[float(request_msg['timestamp'])] = request_msg['id']
        for w in self.workers_['ids']:
            if w == self.id:
                continue
            self.client_.publish(topic=f"/{w}/request", payload=json.dumps(request_msg).encode())
        print(f"{self.id}: critical section access requested with tm-{request_msg['timestamp']}")
        # self.client_.loop_start()
        # sleep(5)
        # self.client_.loop_stop()

        while self.confirmation_ids_.__len__() != (self.workers_['ids'].__len__() - 1) or \
                list(self.critical_queue_.values())[0] != self.id:
            self.client_.loop_read()
            self.client_.loop_write()

        # do teh job
        self.shared_var[self.proc_index] = result
        print(f"{self.id}: got access to critical section")

        for w in self.workers_['ids']:
            self.client_.publish(topic=f"/{w}/release", payload=json.dumps(request_msg).encode())

    def run(self):
        i = 0
        self.stop_ = False
        result = np.zeros((self.cols.shape[0]))
        result_available = False
        while not self.stop_:

            if i < result.shape[0]:
                result[i] = (self.row * self.cols[i]).sum()
                i += 1

                if i == result.shape[0]:
                    print(f"{self.id}: The matmul prod is ready")
                    result_available = True

            if result_available:
                self.lamport_access(result)
                result_available = False
                # msg = {'id': self.id}
                # self.client_.publish(topic=WELL_KNOWN + '/remove', payload=json.dumps(msg).encode())
                self.stop_ = True

            self.client_.loop_read()
            self.client_.loop_write()

        self.client_.loop_start()
