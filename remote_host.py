import sys
import host
import socket
import json
import select
from control_queue import ControlQueue
from logger import *
from model import *

init_stdoutlog()

class RemoteClient:

    def __init__(self, sock, id):
        self.sock = sock
        self.id = id

    def send(self, type, **kwargs):
        rtn = dict(type = type)
        rtn['args'] = kwargs
        self.sock.send(json.dumps(rtn) + "~")
        log("Sent message %s", rtn)

    def recv(self):
        return self.sock.recv(2048)

class HostReceiver:

    def __init__(self, game):
        self.game = game
        self.event_handlers = dict(
                select_card = self.handle_select,
                deselect_card = self.handle_deselect,
                check_set = self.handle_check,
                yell_set = self.handle_yell,
                request_more = self.handle_request_more,
                start = self.handle_start
        )

    def handle_start(self, sock):
        self.game.fill_board()

    def handle_select(self, sock, card, x, y):
        self.game.select_card(Card(*card), x, y)

    def handle_deselect(self, sock, card, x, y):
        self.game.deselect_card(Card(*card), x, y)

    def handle_check(self, sock):
        self.game.check_set(sock)

    def handle_request_more(self, sock):
        self.game.place_three()

    def handle_yell(self, sock):
        self.game.yell_set(sock)

    def control_loop(self, session):
        for msg, sock in session.message_generator():

            if 'type' not in msg:
                log_warn("No 'type' in msg: %s", msg)
                continue

            if msg['type'] in self.event_handlers:
                try:
                    self.event_handlers[msg['type']](sock, **msg['args'])
                except Exception as e:
                    log_warn("Exception %s encountered handling event %s",
                            e, msg)
                    raise
            else:
                log_warn("Received unknown message type %s", msg['type'])

class RemoteSession:

    NUM_PLAYERS = 2

    def __init__(self, ip, port, num_players=NUM_PLAYERS):
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

    def message_generator(self):

        while True:
            sock, _, _= select.select([c.sock for c in self.clients], [], [])
            print(type(sock[0]), type(self.clients[0].sock))
            client = [c for c in self.clients if c.sock == sock[0]][0]

            msg = ''
            while not '~' in msg:
                msg += client.recv()

            messages = msg.split('~')
            for msg in messages[:-1]:
                yield json.loads(msg), client

    def send(self, type, *args, **kwargs):
        for client in self.clients:
            client.send(type, *args, **kwargs)

    def remove_card(self, card, x, y):
        self.send('remove', card=card.properties, x=x, y=y)

    def select_card(self, card, x, y):
        self.send('select', card=card.properties, x=x, y=y)

    def deselect_card(self, card, x, y):
        self.send('deselect', card=card.properties, x=x, y=y)

    def place_card(self, card, x, y):
        self.send('place', card=card.properties, x=x, y=y)

    def yell_set(self, client):
        client.send('self_set_yelled')
        for client2 in self.clients:
            if client2 != client:
                client2.send('show_message', message='Other player yelled set!')


    def send_scores(self, scores):
        for client in self.clients:
            cscores = { 'p{}'.format(id) if id != client.id else 'you': score for id, score in scores.items()}
            client.send('score_update', scores=cscores)

    def too_late(self, client):
        client.send('show_message', message='Too late! Already been called!')
        for client2 in self.clients:
            if client2 != client:
                client2.send('show_message', message='Player {0.id} tryed to yell SET'.format(client))

    def resume_play(self):
        self.send('resume')

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