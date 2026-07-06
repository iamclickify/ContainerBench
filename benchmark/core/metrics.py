import time


class Timer:

    def __init__(self):
        self.start = 0
        self.end = 0

    def start_timer(self):
        self.start = time.perf_counter()

    def stop_timer(self):
        self.end = time.perf_counter()

    @property
    def elapsed(self):
        return round(self.end - self.start, 3)