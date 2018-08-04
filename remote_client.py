import json
import curses
import socket
import ui
from threading import Thread
from control_queue import ControlQueue
from logger import *

init_logfile("53T_client.log")

class RemoteHost:

    def __init__(self, port, queue):
        self.sock = socket.socket()
        self.sock.connect(('127.0.0.1', port))
        self.queue = queue

    def receive_loop(self):
        msg_buffer = ''
        while True:
            while not '~' in msg_buffer:
                msg_buffer += self.sock.recv(1024)
            log("Received %s", msg_buffer)

            messages = msg_buffer.split('~')
            for msg in messages:
                if len(msg) > 0:
                    self.queue.raw_enqueue(msg)
            msg_buffer = ''

    def send(self, type, *args, **kwargs):
        rtn = dict(type=type)
        rtn['args'] = kwargs
        self.sock.send(json.dumps(rtn))
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

def run_client(stdscr):
    ui.Color.init()
    board = ui.Board(stdscr)
    board.init()

    queue = ControlQueue()

    remote_host = RemoteHost(9999, queue)

    controller = ui.LocalController(board, remote_host, queue)

    control_thread = Thread(target = controller.control_loop,
                            args = (stdscr,))

    control_thread.start()

    remote_host.start()
    remote_host.receive_loop()

    control_thread.join()


if __name__ == '__main__':
    curses.wrapper(run_client)
