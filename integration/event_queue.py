
# event_queue.py

from queue import Queue, Full, Empty


class PPEEventQueue:

    def __init__(self, maxsize=1000):
        self.queue = Queue(maxsize=maxsize)

    def enqueue(self, event):
        try:
            self.queue.put_nowait(event)
            return True
        except Full:
            return False

    def dequeue(self):
        try:
            return self.queue.get_nowait()
        except Empty:
            return None

    def task_done(self):
        self.queue.task_done()

    def size(self):
        return self.queue.qsize()

    def is_empty(self):
        return self.queue.empty()
