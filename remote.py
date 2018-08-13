import json
import select
from functools import partial
from logger import *

class RPCSender:

    def __init__(self, methods):
        for method_name in methods:
            log("Registering method %s", method_name)
            setattr(self, method_name, partial(self.send, method_name))

    def send(self, type, *args, **kwargs):
        rtn = dict(type = type, args=args, kwargs=kwargs)
        rtn = json.dumps(rtn) + '~'
        self.sock.send(rtn)
        log('Sent message %s' % rtn)


def recv_iter(sock_map):
    sockets = sock_map.keys()

    while True:
        log("Selecting on %d sockets", len(sockets))
        socks, _, errs = select.select(sockets, [], sockets)
        if len(errs) > 0:
            log("Error occurred on socket!")
            return

        sock = socks[0]

        client =  sock_map[sock]
        log("client %s responded", client)

        msg = ''
        while not msg.endswith('~'):
            msg = ''
            new_msg = sock.recv(2048)
            if len(new_msg) == 0:
                log_warn("Did not receive anything! Error likely. Exiting")
                return
            msg += new_msg
            if not msg.endswith('~'):
                log_warn("Did not receive full message: %s", msg)
                continue

            messages = msg.split('~')
            for message in messages:
                try:
                    yield json.loads(message), client
                except Exception as e:
                    log_warn("Could not load JSON from %s", message)


