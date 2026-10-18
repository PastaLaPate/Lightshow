from collections import deque
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass

from lightshow.core.logger import Logger


@dataclass
class Op:
    undo: Callable[[], None]
    redo: Callable[[], None]


@dataclass
class Entry:
    label: str
    ops: list[Op]


logger = Logger("History")


class History:
    def __init__(self, limit: int = 200):
        self._undo: deque[Entry] = deque(maxlen=limit)
        self._redo: list[Entry] = []
        self._open: list[Op] | None = None

    @contextmanager
    def transaction(self, label: str):
        if self._open is not None:
            yield
            return

        self._open = []
        try:
            yield
        except Exception:
            for op in reversed(self._open):
                op.undo()
            raise
        finally:
            ops, self._open = self._open, None
        if ops:
            self._undo.append(Entry(label, ops))
            self._redo.clear()

    def record(self, undo: Callable[[], None], redo: Callable[[], None]):
        if self._open is None:
            raise RuntimeError("Must open a transaction before recording.")
        self._open.append(Op(undo, redo))

    def undo(self):
        self.debug_dump()
        if len(self._undo) < 1:
            return
        entry = self._undo.pop()
        for op in reversed(entry.ops):
            op.undo()
        self._redo.append(entry)

    def redo(self):
        if len(self._redo) < 1:
            return
        entry = self._redo.pop()
        for op in entry.ops:
            op.redo()
        self._undo.append(entry)

    def debug_dump(self):
        logger.debug("=====HISTORY=====")
        logger.debug("UNDO ENTRIES :")
        for entry in self._undo:
            logger.debug(f"  {entry.label} OPS: {entry.ops}")


global_history = History()
