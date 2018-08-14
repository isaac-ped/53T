import sys
import time
import json
import curses
import socket
import ui
from threading import Thread
from control_queue import ControlQueue
from remote import RPCSender, msg_generator
from logger import *

init_logfile("53T_client.log")

class RemoteHost(RPCSender):

    CALLS = ('select_card', 'deselect_card', 'check_set', 'yell_set', 'request_more', 'start', 'disconnect')

    def __init__(self, ip, port, queue):
        RPCSender.__init__(self, self.CALLS)
        connected = False

        while not connected:
            try:
                log("Attmepting to connect")
                self.sock = socket.socket()
                self.sock.connect((ip, port))
                log("Connected")
                connected = True
            except socket.error:
                self.sock.close()
                log("...")
                time.sleep(1)
        self.queue = queue

    def send(self, msg):
        self.sock.send(msg)

    def receive_loop(self):
        for msg, _ in msg_generator({self.sock: 'host'}):
            log("Received message %s from host", msg)
            self.queue.enqueue_obj(msg)
        log_warn("RECEIVE LOOP EXITED!")
        self.queue.enqueue_msg('end_game', message="Host disconnected")

def run_client(stdscr, ip='127.0.0.1'):

    queue = ControlQueue()

    remote_host = RemoteHost(ip, 9999, queue)

    ui.Color.init()
    board = ui.Board(stdscr)
    board.init()

    controller = ui.LocalController(board, remote_host, queue)

    rtn = []
    control_thread = Thread(target = controller.control_loop,
                            args = (stdscr, rtn))

    control_thread.start()

    remote_host.start()
    remote_host.receive_loop()

    control_thread.join()

    log("Exiting run_client()")

    if len(rtn) > 0:
        return rtn[0]


if __name__ == '__main__':
    if (sys.version_info > (3, 0)):
        print("53T Doesn't look as good with python 3 as python 2 because I can't figure out unicode!")
        print("Proceed at your own risk!")
        time.sleep(5)
    if len(sys.argv) > 1:
        ip = sys.argv[1]
    else:
        ip = '127.0.0.1'
    rtn = curses.wrapper(run_client, ip)
    log("Exited...")
    print("Exited with message: " + str(rtn))
