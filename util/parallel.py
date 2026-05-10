import multiprocessing
import multiprocessing.connection
from collections.abc import Sequence


class Parallel:
    CARRY: int = +2
    BREAK: int = -2

    def __init__(self, target, args: Sequence|None=None):
        self._conn_outer: multiprocessing.connection.Connection
        self._conn_inner: multiprocessing.connection.Connection
        self._conn_outer, self._conn_inner = multiprocessing.Pipe()
        args = () if not args else args
        self._process: multiprocessing.Process = multiprocessing.Process(
            target=target, args=tuple(list(args) + [self._conn_inner])
        )

    def start(self):
        self._process.start()

    def start_and_wait(self):
        self.start()
        return self.recv()

    def is_alive(self):
        return self._process.is_alive()

    def join(self, timeout: float|None = None):
        self._process.join(timeout)

    def send(self, obj):
        if not self.is_alive(): return
        self._conn_outer.send(obj)

    def recv(self):
        if not self.is_alive(): return
        return self._conn_outer.recv()

    def close(self, timeout: float|None = None):
        if self.is_alive():
            self.send(Parallel.BREAK)
            self.join(timeout)
            self._conn_inner.close()
            self._conn_outer.close()
