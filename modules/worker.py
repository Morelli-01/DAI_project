import socket
import threading
import time
from base64 import encode
from multiprocessing import Value
from time import sleep

import numpy as np


def extract_token(decoded_data):
    return int(decoded_data[decoded_data.find('{') + 1: decoded_data.find('}')])


class Worker(threading.Thread):
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
