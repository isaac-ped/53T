import signal
import sys
import time
import ui
import host
from control_queue import ControlQueue
import curses
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

class LocalSession:

    def __init__(self, ctl_queue):
        self.ctl_queue = ctl_queue
        self.clients = [LocalClient(1)]

    def remove_card(self, card, x, y):
        log("Locally removing card at %d, %d", x, y)
        self.ctl_queue.enqueue("remove", card=card.properties, x=x, y=y)

    def select_card(self, card, x, y):
        log("Locally selecting card at %d, %d", x, y)
        self.ctl_queue.enqueue("select", card=card.properties, x=x, y=y)

    def deselect_card(self, card, x, y):
        log("Locally deselecting card at %d, %d", x, y)
        self.ctl_queue.enqueue("deselect", card=card.properties, x=x, y=y)

    def place_card(self, card, x, y):
        log("Locally enqueueing placing card %s at %d, %d", card, x, y)
        self.ctl_queue.enqueue("place", card=card.properties, x=x, y=y)

    def yell_set(self, client_id):
        log("Yelling SET!")
        self.ctl_queue.enqueue("self_set_yelled")

    def resume_play(self):
        log("Resuming...")
        self.ctl_queue.enqueue("resume")

    def send_scores(self, scores):
        self.ctl_queue.enqueue('score_update', scores=scores)

    def end_game(self, scores):
        txt = 'Final score: {}'.format(scores.values())
        self.ctl_queue.enqueue('show_message', message=txt)


class LocalHost:

    def __init__(self, game):
        self.game = game

    def start(self):
        self.game.fill_board()

    def yell_set(self):
        self.game.yell_set(None)

    def select_card(self, card, x, y):
        self.game.select_card(card, x, y)

    def deselect_card(self, card, x, y):
        self.game.deselect_card(card, x, y)

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
