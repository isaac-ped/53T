import sys
import host
import socket
import json
import select
from remote import RPCSender, MsgHandler,  msg_generator
from control_queue import ControlQueue
from logger import *
from model import *

init_stdoutlog()

class RemoteClient:

    def __init__(self, sock, id):
        self.sock = sock
        self.id = id

        self.send(json.dumps(dict(type="client_id", args=[id], kwargs={}))+ '~')

    def send(self, msg):
        self.sock.send(msg)
        log("Sent message %s", msg)

    def recv(self):
        return self.sock.recv(2048)

class HostReceiver():

    H = MsgHandler()

    def __init__(self, game):
        self.game = game
        self.H.bind(self)

        self.event_handlers = dict(
                select_card = self.handle_select,
                deselect_card = self.handle_deselect,
                check_set = self.handle_check,
                yell_set = self.handle_yell,
                request_more = self.handle_request_more,
                start = self.handle_start
        )

    @H.register('start')
    def handle_start(self, sock):
        log("Handling start message")
        self.game.fill_board()

    @H.register('select_card')
    def handle_select(self, sock, card, x, y):
        self.game.select_card(Card(*card), x, y)

    @H.register('deselect_card')
    def handle_deselect(self, sock, card, x, y):
        self.game.deselect_card(Card(*card), x, y)

    @H.register('check_set')
    def handle_check(self, sock):
        self.game.check_set(sock)

    @H.register('request_more')
    def handle_request_more(self, sock):
        self.game.place_three()

    @H.register('yell_set')
    def handle_yell(self, client):
        self.game.yell_set(client)

    def control_loop(self, session):
        for msg, client in session.generate_messages():
            self.H.handle(msg['type'], [client] + msg['args'], msg['kwargs'])


class RemoteSession(RPCSender):

    NUM_PLAYERS = 2

    CALLS = ( 'remove', 'select', 'deselect', 'place', 'set_yelled', 'score_update', 'set_stolen', 'too_late', 'end_game', 'resume')

    def __init__(self, ip, port, num_players=NUM_PLAYERS):
        RPCSender.__init__(self, self.CALLS)
        self.port = port
        #create an INET, STREAMing socket
        serversocket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind((ip, port))
        log("Bound to %d", port)
        #become a server socket
        serversocket.listen(10)

        self.clients = []
        for id in range(num_players):
            log("Listening...")
            conn, _ = serversocket.accept()
            log("Accepted connection!")
            self.clients.append(RemoteClient(conn, id + 1))

    def generate_messages(self):
        sock_map = {c.sock : c for c in self.clients}
        for msg, client in  msg_generator(sock_map):
            yield msg, client

    def send(self, msg):
        for client in self.clients:
            client.send(msg)

ip='127.0.0.1'

def run_host(ip=ip, num_players=2):

    log("Here!")
    session = RemoteSession(ip, 9999, num_players)
    game = host.Game(session)

    receiver = HostReceiver(game)

    receiver.control_loop(session)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Usage: python %s <ip> <# players>" % sys.argv[0])
        exit(1)
    if len(sys.argv) > 2:
        run_host(sys.argv[1], int(sys.argv[2]))
    else:
        run_host(sys.argv[1])
