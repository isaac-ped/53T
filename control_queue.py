try:
    from queue import Queue
except:
    # Python 3 changed capitalization O_o
    from Queue import Queue
from logger import *
import json

class ControlQueue:

    def __init__(self):
        self.queue = Queue()

    def raw_enqueue(self, msg):
        self.queue.put(msg)

    def enqueue(self, type, **kwargs):
        rtn = dict(type = type)
        rtn['args'] = kwargs
        self.queue.put(json.dumps(rtn))
        log("Enqueueing message %s", rtn)

    def dequeue(self):
        log("Attempting dequeue")
        msg_s = self.queue.get(True)
        msg = json.loads(msg_s)
        log("Dequeueing message %s", msg_s)
        return msg


