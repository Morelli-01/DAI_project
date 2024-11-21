from numpy import ndarray
from paho.mqtt.client import Client
import paho.mqtt.client as mqtt
from modules.worker import RingWorker, MqttWorker, MqttDeviceDiscovery
from random import randint
from multiprocessing import shared_memory, cpu_count
import numpy as np
import time, json
from prettytable import PrettyTable

WELL_KNOWN = '/.well-known'
N_PROCESSES = 2
DEBUG = False


class Ring_Mutex():
    def __init__(self, m1: ndarray, m2: ndarray, debug=False):
        self.N_PROCESSES = m1.shape[0]
        self.m1 = m1
        self.m2 = m2
        self.out_mat = np.zeros((m1.shape[0], m2.shape[1]))
        self.shmem_ = shared_memory.SharedMemory(create=True, size=self.out_mat.nbytes)
        self.shared_matrix = np.ndarray(self.out_mat.shape, dtype=self.out_mat.dtype, buffer=self.shmem_.buf)
        self.shared_matrix[:] = self.out_mat
        self.workers = []
        self.used_ports = []
        self.debug = debug

        self.ring_init_()

    def ring_init_(self):
        while len(self.workers) < self.N_PROCESSES:
            casual_port = randint(3000, 8000)
            while (self.used_ports.__contains__(casual_port)):
                casual_port = randint(3000, 8000)
            self.used_ports.append(casual_port)

            host = "localhost"
            next_worker = ("", None)

            if len(self.workers) > 0:
                next_worker = self.workers[len(self.workers) - 1]
                next_worker = (next_worker.host, next_worker.port)

            w = RingWorker(host=host, port=casual_port, next_host=next_worker, debug=False,
                           shared_var=self.shared_matrix)
            self.workers.append(w)

        next_worker = self.workers[len(self.workers) - 1]
        next_worker = (next_worker.host, next_worker.port)
        self.workers[0].next_host = next_worker
        if self.debug:
            print(f"{len(self.workers)} processes have been created")

    def start(self):
        start = time.time()
        for i in range(1, len(self.workers)):
            self.workers[i].assign_work(self.m1[i], self.m2, i)
            self.workers[i].start()

        self.workers[0].assign_work(self.m1[0], self.m2, 0)
        self.workers[0].starter(N_PROCESSES)

        for w in self.workers:
            w.join()

        end = time.time()
        length = end - start
        t = PrettyTable(['Name', 'Value'])
        t.add_row(['Processes', N_PROCESSES])
        t.add_row(['Elapsed Time(s)', length])
        t.add_row(['Ring Full Cycles', self.workers[0].cycles_counter])
        t.add_row(['Token passages', self.workers[0].cycles_counter * N_PROCESSES])
        print(t)

        if self.debug:
            for w in self.workers:
                print(w.event_history)


class Lamport_Mutex():
    def __init__(self, m1: ndarray, m2: ndarray, debug=False):
        self.N_PROCESSES = m1.shape[0]
        self.m1 = m1
        self.m2 = m2
        self.out_mat = np.zeros((m1.shape[0], m2.shape[1]))
        self.shmem_ = shared_memory.SharedMemory(create=True, size=self.out_mat.nbytes)
        self.shared_matrix = np.ndarray(self.out_mat.shape, dtype=self.out_mat.dtype, buffer=self.shmem_.buf)
        self.shared_matrix[:] = self.out_mat
        self.workers = []
        self.debug = debug

        self.device_dicovery = MqttDeviceDiscovery(id_client='device-dicovery', debug=DEBUG)
        self.device_dicovery.start()

        i = 0
        while len(self.workers) < self.N_PROCESSES:
            w_ = MqttWorker(debug=DEBUG, shared_var=self.shared_matrix, id_client=f"Thread-{i}")
            self.workers.append(w_)
            i += 1

        if self.debug:
            print(f"{len(self.workers)} processes have been created")

    def start(self):
        for i in range(len(self.workers)):
            self.workers[i].assign_work(self.m1[i], self.m2, i)
            self.workers[i].start()

        for w in self.workers:
            w.join()

        if self.debug:
            for w in self.workers:
                print(w.event_history)


if __name__ == "__main__":
    mat1 = np.random.randint(1, 11, (N_PROCESSES, 20))
    mat2 = np.random.randint(1, 11, (20, 2000))

    # rm_ = Ring_Mutex(mat1, mat2, debug=DEBUG)
    # rm_.start()
    #
    start = time.time()
    res_mat = mat1.dot(mat2)
    end = time.time()
    length = end - start
    t = PrettyTable(['Name', 'Value'])
    t.add_row(['Processes', 1])
    t.add_row(['Elapsed Time(s)', length])
    # print(t)
    # print(shared_matrix)
    # if (res_mat == rm_.shared_matrix).all():
    #     print(f"The Shared_matrix contains the correct result")

    lm_ = Lamport_Mutex(mat1, mat2, True)
    lm_.start()
    if (res_mat == lm_.shared_matrix).all():
        print(f"The Shared_matrix contains the correct result")
