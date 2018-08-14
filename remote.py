import json
import select
from functools import partial
from logger import *
import traceback 
class RPCSender:

    def __init__(self, methods):
        for method_name in methods:
            log("Registering method %s", method_name)
            setattr(self, method_name, partial(self._send, method_name))

    def _send(self, type, *args, **kwargs):
        rtn = dict(type = type, args=args, kwargs=kwargs)
        rtn = json.dumps(rtn) + '~'
        self.send(rtn)
        log('Sent message %s' % rtn)


def msg_generator(sock_map):
    sockets = sock_map.keys()

    while True:
        log("Selecting on %d sockets", len(sockets))
        try:
            socks, _, errs = select.select(sockets, [], sockets)
            if len(errs) > 0:
                log("Error occurred on socket!")
                return
        except:
            continue
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
                if len(message) == 0:
                    continue
                try:
                    yield json.loads(message), client
                except Exception as e:
                    log_warn("Could not load JSON from %s", message)


class MsgHandler(object):

    def __init__(self):
        self.handlers = {}
        self.args = []

    def bind(self, *args):
        self.args = list(args)

    def register(self, label):
        def inner(fn):
            self.handlers[label] = fn
            return fn
        return inner

    def handle(self, type, args, kwargs):
        args = self.args[:] + list(args)
        if type in self.handlers:
            try:
                log("Handling message %s" %[type, args, kwargs])
                return self.handlers[type](*args, **kwargs)
            except Exception as e:
                log_warn("Exception %s encondered handling event %s", e, [type, [self.args] + args, kwargs])
                log_warn(traceback.format_exc())
                raise
        else:
            log_warn("Received unknown message type: %s", type)


