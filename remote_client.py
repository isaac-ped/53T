import sys
import time
import json
import curses
import socket
import ui
from threading import Thread
from control_queue import ControlQueue
from logger import *

init_logfile("53T_client.log")

class RemoteHost:

    def __init__(self, ip, port, queue):
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

    def receive_loop(self):
        msg_buffer = ''
        while True:
            while not '~' in msg_buffer:
                try:
                    msg_buffer += self.sock.recv(1024)
                except socket.error as e:
                    log("Got error reading socket: %s" % e)

            log("Received %s", msg_buffer)

            messages = msg_buffer.split('~')
            for msg in messages:
                if len(msg) > 0:
                    self.queue.raw_enqueue(msg)
            msg_buffer = ''

    def send(self, type, *args, **kwargs):
        rtn = dict(type=type)
        rtn['args'] = kwargs
        self.sock.send(json.dumps(rtn) + '~')
        log("Sent message %s" % rtn)

    def select_card(self, card, x, y):
        self.send('select_card', card=card.properties, x=x, y=y)

    def deselect_card(self, card, x, y):
        self.send('deselect_card', card=card.properties, x=x, y=y)

    def check_set(self):
        self.send('check_set')

    def yell_set(self):
        self.send('yell_set')

    def request_more(self):
        self.send('request_more')

    def start(self):
        self.send('start')

ip = '127.0.0.1'

def run_client(stdscr):

    queue = ControlQueue()

    remote_host = RemoteHost(ip, 9999, queue)

    ui.Color.init()
    board = ui.Board(stdscr)
    board.init()

    controller = ui.LocalController(board, remote_host, queue)

    control_thread = Thread(target = controller.control_loop,
                            args = (stdscr,))

    control_thread.start()

    remote_host.start()
    remote_host.receive_loop()

    control_thread.join()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        ip = sys.argv[1]
    curses.wrapper(run_client)
