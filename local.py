import gui
import host
from common import ControlQueue
import curses
from logger import *
from threading import Thread

class Controller:

    KEYS = [
            ['1', '2', '3', '4', '5'],
            ['q', 'w', 'e', 'r', 't'],
            ['a', 's', 'd', 'f', 'g'],
            ['z', 'x', 'c', 'v', 'b'],
        ]

class LocalSession:

    def __init__(self, ctl_queue):
        self.ctl_queue = ctl_queue

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
        self.ctl_queue.enqueue("yell_set")

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
        self.game.check_set()

def run_local(stdscr):
    gui.Color.init()
    board = gui.Board(stdscr)
    board.init()

    queue = ControlQueue()

    session = LocalSession(queue)

    game = host.Game(session)

    local_host = LocalHost(game)

    controller = gui.LocalController(board, local_host, queue)

    control_thread = Thread(target = controller.control_loop,
                            args = (stdscr,))
    control_thread.start()

    local_host.start()

    control_thread.join()

if __name__ == '__main__':
    curses.wrapper(run_local)
