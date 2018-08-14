import signal
import sys
import time
import ui
import host
from model import Card
from control_queue import ControlQueue
import curses
from remote import RPCSender
import json
from logger import *
from threading import Thread

init_logfile("53T_local.log")

def interrupt_handler(signum, frame):
    log("INTERRUPTED!")
    exit(-1)

signal.signal(signal.SIGINT, interrupt_handler)

class LocalClient:

    def __init__(self, id):
        self.id = id

class LocalSession(RPCSender):

    CALLS = ('remove', 'select', 'deselect', 'place', 'set_yelled', 'score_update', 'set_stolen',
             'too_late', 'end_game', 'resume')

    def __init__(self, ctl_queue):
        RPCSender.__init__(self, self.CALLS)
        self.ctl_queue = ctl_queue
        self.clients = [LocalClient(1)]
        self.ctl_queue.enqueue_obj(dict(type='client_id', args=[1], kwargs={}))

    def send(self, msg):
        jmsg = json.loads(msg[:-1])
        self.ctl_queue.enqueue_obj(jmsg)


class LocalHost:

    def __init__(self, game):
        self.game = game

    def start(self):
        self.game.fill_board()

    def yell_set(self):
        self.game.yell_set(LocalClient(1))

    def select_card(self, card, x, y):
        self.game.select_card(Card(*card), x, y)

    def deselect_card(self, card, x, y):
        self.game.deselect_card(Card(*card), x, y)

    def check_set(self):
        self.game.check_set(LocalClient(1))

    def request_more(self):
        self.game.place_three()

def run_local(stdscr):
    ui.Color.init()
    board = ui.Board(stdscr)
    board.init()

    queue = ControlQueue()

    session = LocalSession(queue)

    game = host.Game(session)

    local_host = LocalHost(game)

    controller = ui.LocalController(board, local_host, queue)

    control_thread = Thread(target = controller.control_loop,
                            args = (stdscr,))
    control_thread.start()

    signal.signal(signal.SIGINT, interrupt_handler)
    local_host.start()

    control_thread.join()

if __name__ == '__main__':
    if (sys.version_info > (3, 0)):
        print("53T Doesn't look as good with python 3 as python 2 because I can't figure out unicode!")
        print("Proceed at your own risk!")
        time.sleep(5)
    curses.wrapper(run_local)
