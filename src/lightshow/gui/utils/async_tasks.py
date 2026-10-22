import threading
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThread, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QApplication

from lightshow.core.logger import Logger

logger = Logger("TaskRunner")


class TaskCancelled(Exception):
    pass


class CancelToken:
    def __init__(self):
        self.event = threading.Event()

    def cancel(self):
        self.event.set()

    @property
    def cancelled(self) -> bool:
        return self.event.is_set()


class TaskContext:
    def __init__(
        self, token: CancelToken, post_progress: Callable[[str, float | None], None]
    ):
        self._token = token
        self._progress_cb = post_progress

    def progress(self, msg: str, fraction: float | None = None):
        self._progress_cb(msg, fraction)

    @property
    def cancelled(self) -> bool:
        return self._token.cancelled

    def check(self):
        if self._token.cancelled:
            raise TaskCancelled()


class _Bridge(QObject):
    call = Signal(object)

    def __init__(self):
        super().__init__()
        self.call.connect(self._invoke)

    @Slot(object)  # Force run in GUI thread
    def _invoke(self, fn: Callable):
        fn()


class _Job(QRunnable):
    def __init__(self, fn: Callable[[], None]):
        super().__init__()
        self._fn = fn

    def run(self):
        self._fn()


@dataclass
class JobData:
    fn: Callable[..., Any]
    key: str | None = None
    on_done: Callable[[Any], None] | None = None
    on_error: Callable[[Exception], None] | None = None
    on_progress: Callable[[str, float | None], None] | None = None
    on_finished: Callable[[], None] | None = None


class TaskRunner:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, pool: QThreadPool | None = None):
        assert (app := QApplication.instance()) is not None
        assert QThread.currentThread() is app.thread(), (
            "TaskRunner must be created in the GUI thread"
        )

        self._bridge = _Bridge()
        self._pool = pool or QThreadPool.globalInstance()
        self._active: dict[str, CancelToken] = {}

    @staticmethod
    def init_singleton(pool: QThreadPool | None = None):
        with TaskRunner._lock:
            if TaskRunner._instance is None:
                TaskRunner._instance = TaskRunner(pool)

    @staticmethod
    def get() -> TaskRunner:
        if TaskRunner._instance is None:
            raise RuntimeError("TaskRunner not initialized. Call init_singleton first.")
        return TaskRunner._instance

    def is_busy(self, key: str) -> bool:
        return key in self._active

    def cancel(self, key: str) -> None:
        if t := self._active.get(key):
            t.cancel()

    def submit(self, data: JobData, *args, **kwargs) -> bool:
        assert QThread.currentThread() is self._bridge.thread(), (
            "submit() must be called from the GUI thread"
        )
        if data.key is not None and data.key in self._active:
            return False

        token = CancelToken()
        if data.key is not None:
            self._active[data.key] = token
        post = self._bridge.call.emit

        def finish(result: Any, error: Exception | None, cancelled: bool):
            if data.key is not None:
                self._active.pop(data.key, None)
            try:
                if error is not None:
                    if data.on_error:
                        data.on_error(error)
                    else:
                        logger.error(f"Unhandled task error {error}")
                elif not cancelled and data.on_done:
                    data.on_done(result)
            finally:
                if data.on_finished:
                    data.on_finished()

        def post_progress(msg: str, frac: float | None):
            if data.on_progress:
                post(partial(data.on_progress, msg, frac))

        def work():
            ctx = TaskContext(token, post_progress)
            try:
                result = data.fn(ctx, *args, **kwargs)
            except TaskCancelled:
                post(lambda: finish(None, None, True))
            except Exception as e:  # noqa
                err = e
                post(lambda: finish(None, err, False))
            else:
                post(lambda: finish(result, None, False))

        self._pool.start(_Job(work))
        return True
