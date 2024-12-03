Description of the Project

The folder contains the DAI_project which simulates the Ring Mutex(rm) algorithm and the Lamport Mutex(lm) algorithm in
order to handle the distributed access to a shared resource.
The algorithms emulate the matrix multiplication(C = A * B), indeed every process receives a row of the matrix A and
the whole matrix B and computes all the row by column multiplications, then once they have computed they're results every
process has to write it in the final shared matrix C which access is handled with the two different algorithm.
The Ring Mutex algorithm is implemented using classic client/server paradigm with sockets meanwhile Lamport Mutex
algorithm is implemented using the pub/sub paradigm through the Mqtt protocol which is more suited with respect
to the classical client/server paradigm.

How to Run it
Before running the program an mqtt broker must be listening on the 1883 port, during the development the mosquitto
broker has been used(https://mosquitto.org/download/) and runned with the command
    mosquitto -p 1883 -v

Once the broker is up the program can be launched with a simple
    python3 main.py
For more insight on what happened during the execution debugs variables can be set as 'true'
    GENERAL_DEBUG low level log infos of both algorithms
    LM_DEBUG high level log about teh Lamport algorithm
    RM_DEBUG high level log about teh Ring algorithm
Moreover also the number of processes generated can be changes with the variable N_PROCESSES that is exactly the
number of rows of the matrx A. Maximum efficiency is achieved when N_PROCESSES correspond to the number of cpu cores.
Aldo the global variable COLUMNS can be changed in order to increase or decrease the workload of the computation since
it command the numer of columns of the matrix A and the number of rows of the matrx B