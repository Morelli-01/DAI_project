import socket
import argparse, subprocess, signal
from numpy import ndarray
from paho.mqtt.client import Client
import paho.mqtt.client as mqtt
from modules.worker import RingWorker, MqttWorker, MqttDeviceDiscovery
from random import randint
from multiprocessing import shared_memory, cpu_count
import numpy as np
import time, json
from prettytable import PrettyTable
from time import sleep
from datetime import datetime
from sortedcontainers import SortedDict

N_PROCESSES = 50
COLUMNS = 100
GENERAL_DEBUG = False
LM_DEBUG = False
RM_DEBUG = False


def is_port_free(port, host='localhost'):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
        return True
    except OSError:
        return False


class Ring_Mutex():
    def __init__(self, m1: ndarray, m2: ndarray, debug=False, correct_result=None, last_port_used=3000):
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
        self.correct_result = correct_result
        self.last_port_used = last_port_used
        self.ring_init_()

    def ring_init_(self):
        while len(self.workers) < self.N_PROCESSES:
            self.last_port_used += 1
            while not is_port_free(self.last_port_used):
                self.last_port_used += 1

            casual_port = self.last_port_used

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
        self.elapsed_time = end - start
        t = PrettyTable(['Name', 'Value'])
        t.add_row(['Algoritm', "Ring"])
        t.add_row(['Processes', N_PROCESSES])
        t.add_row(['Elapsed Time(s)', str(self.elapsed_time)[:5]])
        t.add_row(['Ring Full Cycles', self.workers[0].cycles_counter])
        t.add_row(['Token passages', self.workers[0].cycles_counter * N_PROCESSES])
        self.token_passed = self.workers[0].cycles_counter * N_PROCESSES
        self.mean_access_time = 0
        for w in self.workers:
            self.mean_access_time += w.elapsed_t_with_token
        self.mean_access_time /= self.workers.__len__()
        t.add_row(['Mean Token Held Time(s)', str(self.mean_access_time)[:5]])

        stddev_access_time = 0
        for w in self.workers:
            stddev_access_time += (w.elapsed_t_with_token - self.mean_access_time) ** 2
        t.add_row(['Stddev Token Held Time(s)', str(stddev_access_time / self.workers.__len__())[:5]])

        if self.correct_result is not None:
            correctness = (self.correct_result == self.shared_matrix).all()
            t.add_row(['Correct Result', correctness])
        print(t)

        for w in self.workers:
            w.s.close()
            del w.s

        if self.debug:
            for w in self.workers:
                print(w.event_history)


class Lamport_Mutex():
    def __init__(self, m1: ndarray, m2: ndarray, debug=False, correct_result=None):
        self.N_PROCESSES = m1.shape[0]
        self.m1 = m1
        self.m2 = m2
        self.out_mat = np.zeros((m1.shape[0], m2.shape[1]))
        self.shmem_ = shared_memory.SharedMemory(create=True, size=self.out_mat.nbytes)
        self.shared_matrix = np.ndarray(self.out_mat.shape, dtype=self.out_mat.dtype, buffer=self.shmem_.buf)
        self.shared_matrix[:] = self.out_mat
        self.workers = []
        self.debug = debug
        self.correct_result = correct_result

        self.device_dicovery = MqttDeviceDiscovery(id_client='device-dicovery', debug=GENERAL_DEBUG)
        self.device_dicovery.start()

        i = 0
        while len(self.workers) < self.N_PROCESSES:
            w_ = MqttWorker(debug=GENERAL_DEBUG, shared_var=self.shared_matrix, id_client=f"Thread-{i}")
            self.workers.append(w_)
            i += 1

        if self.debug:
            print(f"{len(self.workers)} processes have been created")

    def start(self):
        start = time.time()

        for i in range(len(self.workers)):
            self.workers[i].assign_work(self.m1[i], self.m2, i)
            self.workers[i].start()

        for w in self.workers:
            while not w.work_done:
                continue

        end = time.time()
        self.elapsed_time = end - start
        t = PrettyTable(['Name', 'Value'])
        t.add_row(['Algoritm', "Lamport"])
        t.add_row(['Processes', N_PROCESSES])
        t.add_row(['Elapsed Time(s)', str(self.elapsed_time)[:5]])

        self.total_msg_sent = 0
        self.mean_access_time = 0
        for w in self.workers:
            self.mean_access_time += w.elapsed_t_with_access
            self.total_msg_sent += w.sent_msg_counter
        self.mean_access_time /= self.workers.__len__()
        t.add_row(['Total Msg Exchanged', str(self.total_msg_sent)[:5]])
        t.add_row(['Mean Access Time(s)', str(self.mean_access_time)[:5]])

        self.stddev_access_time = 0
        for w in self.workers:
            self.stddev_access_time += (w.elapsed_t_with_access - self.mean_access_time) ** 2
        t.add_row(['Stddev Access Time(s)', str(self.stddev_access_time / self.workers.__len__())[:5]])

        if self.correct_result is not None:
            correctness = (self.correct_result == self.shared_matrix).all()
            t.add_row(['Correct Result', correctness])

        print(t)

        for w in self.workers:
            w.del_device()
            w.stop()
            del w

        self.device_dicovery.stop()
        del self.device_dicovery
        request_history = SortedDict()
        access_history = SortedDict()
        if self.debug:
            for w in self.workers:
                if GENERAL_DEBUG:
                    print(w.event_history)

                for m in w.event_history:
                    if m.__contains__("critical section access requested"):
                        request_history[float(
                            m[m.find('tm-') + 4:])] = f"[{m[m.find('[') + 1:m.find(']')]}]{m[16:m.find("crit") - 2]}"
                    if m.__contains__("got access to critical section"):
                        t = float(m[m.find('(') + 1:m.find(')')])
                        access_history[t] = f"[{m[m.find('[') + 1:m.find(']')]}]{m[16:m.find("got") - 2]}"
                w.del_device()

        # for i in range(len(request_history)):
        #     m = request_history[i]
        #     t = datetime.fromtimestamp(float(m[m.find('tm-')+4:]), tz=None)
        #     request_history[i] = f"[{t.time()}]{m[16:24]}"
        if self.debug:
            print("Request History")
            print(json.dumps(request_history, sort_keys=True, indent=4))
            print("Access History")
            print(json.dumps(access_history, sort_keys=True, indent=4))


if __name__ == "__main__":
    last_port_used = 3000
    parser = argparse.ArgumentParser()

    parser.add_argument('--n_proc', type=int, required=True)
    parser.add_argument('--type', type=str, choices=['np', 'token-ring', 'lamport'], help="algo type", required=True)
    parser.add_argument('--columns', type=int, help="")
    args = parser.parse_args()

    N_PROCESSES = args.n_proc

    if args.columns is not None:
        COLUMNS = int(args.columns)

    mat1 = np.random.randint(1, 11, (N_PROCESSES, COLUMNS))
    mat2 = np.random.randint(1, 11, (COLUMNS, 2000))

    start = time.time()

    res_mat = mat1.dot(mat2)
    end = time.time()
    length = end - start
    t = PrettyTable(['Name', 'Value'])
    t.add_row(['Algoritm', "np.matmul"])
    t.add_row(['Processes', 1])
    t.add_row(['Elapsed Time(s)', length])
    if args.type == 'np':

        print(t)

    elif args.type == 'token-ring':
        rm_ = Ring_Mutex(mat1, mat2, debug=RM_DEBUG, last_port_used=last_port_used, correct_result=res_mat)
        rm_.start()
        assert (res_mat == rm_.shared_matrix).all(), f"The RingMutex Shared_matrix is not correct\n"
        last_port_used = rm_.last_port_used

        # rm_.shmem_.close()
        # del rm_.shared_matrix
        # del rm_.shmem_
        # del rm_

    elif args.type == 'lamport':
        mosquitto_proc = subprocess.Popen(
            ["mosquitto", "-v", "-p", str(1883)],
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE
        )
        sleep(1)

        lm_ = Lamport_Mutex(mat1, mat2, debug=LM_DEBUG, correct_result=res_mat)
        sleep(2)
        lm_.start()
        assert (res_mat == lm_.shared_matrix).all(), f"The RingMutex Shared_matrix is not correct\n"
        lm_.shmem_.close()
        del lm_.shared_matrix
        del lm_.shmem_
        del lm_

        mosquitto_proc.send_signal(signal.SIGINT)
        mosquitto_proc.wait()
