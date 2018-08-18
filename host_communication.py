import sys
import host
import socket
import json
import select
from remote import RPCSender, MsgHandler,  msg_generator
from control_queue import ControlQueue
from host import Game
from logger import *
from model import *


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

class HostReceiver(object):

    H = MsgHandler()

    def __init__(self, game):
        self.game = game
        self.H.bind(self)

    @H.register('start')
    def handle_start(self, client):
        log("Handling start message")
        return self.game.fill_board()

    @H.register('select_card')
    def handle_select(self, client, card, x, y):
        return self.game.select_card(Card(*card), x, y)

    @H.register('deselect_card')
    def handle_deselect(self, client, card, x, y):
        return self.game.deselect_card(Card(*card), x, y)

    @H.register('check_set')
    def handle_check(self, client):
        return self.game.check_set(client)

    @H.register('request_more')
    def handle_request_more(self, client):
        return self.game.request_more(client)

    @H.register('yell_set')
    def handle_yell(self, client):
        return self.game.yell_set(client)

    @H.register('disconnect')
    def handle_disconnect(self, client):
        return self.game.disconnect(client)

    def control_loop(self, session):
        for msg, client in session.generate_messages():
            rtn = self.H.handle(msg['type'], [client] + msg['args'], msg['kwargs'])
            if rtn == True:
                return True

class RemoteSession(RPCSender):

    NUM_PLAYERS = 2

    def __init__(self, ip, port, num_players=NUM_PLAYERS):
        RPCSender.__init__(self, Game.SESSION_CALLS)
        self.port = port
        self.num_clients = num_players
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

    def client_ids(self):
        for client in self.clients:
            yield client.id

    def generate_messages(self):
        sock_map = {c.sock : c for c in self.clients}
        for msg, client in  msg_generator(sock_map):
            yield msg, client

    def send(self, msg):
        for client in self.clients:
            client.send(msg)

def run_host(ip='127.0.0.1', num_players=2):

    log("Here!")
    session = RemoteSession(ip, 9999, int(num_players))
    game = host.Game(session)

    receiver = HostReceiver(game)

    receiver.control_loop(session)

if __name__ == '__main__':
    init_stdoutlog()
    if len(sys.argv) > 3 :
        print("Usage: python %s [ip] [# players]" % sys.argv[0])
        exit(1)
    run_host(*sys.argv[1:])
