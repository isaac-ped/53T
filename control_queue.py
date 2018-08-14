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
        self.exiting = False

    def signal_exit(self):
        log("Exit signaled in queue")
        self.exiting = True

    def enqueue_obj(self, obj):
        log("Putting object %s in queue", obj)
        self.queue.put(obj)

    def enqueue_msg(self, type, *args, **kwargs):
        rtn = dict(type = type, args=args, kwargs=kwargs)
        log("Putting message %s in queue", rtn)
        self.queue.put(rtn)

    def dequeue(self):
        log("Attempting dequeue")
        msg = self.queue.get(True)
        log("Dequeueing message %s", msg)
        return msg


