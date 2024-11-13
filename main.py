from numpy import ndarray

from modules.worker import Worker
from random import randint
from multiprocessing import shared_memory, cpu_count
import numpy as np
import time
from prettytable import PrettyTable

N_PROCESSES = 16
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

            w = Worker(host=host, port=casual_port, next_host=next_worker, debug=self.debug, shared_var=self.shared_matrix)
            self.workers.append(w)

        next_worker = self.workers[len(self.workers) - 1]
        next_worker = (next_worker.host, next_worker.port)
        self.workers[0].next_host = next_worker
        if self.debug:
            print(f"{len(self.workers)} processes have been created")

    def start(self):
        start = time.time()
        for i in range(1, len(self.workers)):
            self.workers[i].assign_work(mat1[i], mat2, i)
            self.workers[i].start()

        self.workers[0].assign_work(mat1[0], mat2, 0)
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



if __name__ == "__main__":

    mat1 = np.random.randint(1, 11, (N_PROCESSES, 20000))
    mat2 = np.random.randint(1, 11, (20000, 2000))

    rm_ = Ring_Mutex(mat1, mat2, debug=DEBUG)
    rm_.start()

    start = time.time()
    res_mat = mat1.dot(mat2)
    end = time.time()
    length = end - start
    t = PrettyTable(['Name', 'Value'])
    t.add_row(['Processes', 1])
    t.add_row(['Elapsed Time(s)', length])
    print(t)
    # print(shared_matrix)
    if (res_mat == rm_.shared_matrix).all():
        print(f"The Shared_matrix contains the correct result")
