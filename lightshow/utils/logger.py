import logging
import threading
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional

# ---------------------------------------------------------------------------
# Formatters & Filters
# ---------------------------------------------------------------------------


class _ColorFormatter(logging.Formatter):
    _COLORS = {
        logging.DEBUG: "\x1b[90m",
        logging.INFO: "\x1b[37m",
        logging.WARNING: "\x1b[93m",
        logging.ERROR: "\x1b[91m",
        logging.CRITICAL: "\x1b[31;1m",
    }
    _RESET = "\x1b[0m"
    _FMT = "%(asctime)s [%(appname)s] [%(shortname)s] [%(levelname)s] : %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        color = self._COLORS.get(record.levelno, self._RESET)
        formatter = logging.Formatter(
            f"{color}{self._FMT}{self._RESET}", datefmt="%H:%M:%S"
        )
        return formatter.format(record)


class _PlainFormatter(logging.Formatter):
    _FMT = "%(asctime)s [%(appname)s] [%(shortname)s] [%(levelname)s] : %(message)s"

    def __init__(self):
        super().__init__(self._FMT, datefmt="%H:%M:%S")


class _ContextFilter(logging.Filter):
    """Injects shortname and appname into every record."""

    def __init__(self, app_name: str):
        super().__init__()
        self.app_name = app_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.shortname = record.name.split(".")[-1]  # last segment only
        record.appname = self.app_name
        return True


# ---------------------------------------------------------------------------
# Qt handler — pushes HTML into a queue, drained by the GUI thread
# ---------------------------------------------------------------------------


class _QtQueueHandler(logging.Handler):
    _COLORS = {
        logging.DEBUG: "#9b9b9b",
        logging.INFO: "#ffffff",
        logging.WARNING: "#ffcc00",
        logging.ERROR: "#ff4444",
        logging.CRITICAL: "#ff0000",
    }

    def __init__(self, queue: Queue):
        super().__init__()
        self._queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            color = self._COLORS.get(record.levelno, "#ffffff")
            html = f'<span style="color:{color}">{msg}</span>'
            is_fps = "Average fps" in record.getMessage()
            self._queue.put_nowait((html, is_fps))
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------------------------
# Root configurator (once per process)
# ---------------------------------------------------------------------------


class _RootLoggerConfig:
    _instance: Optional["_RootLoggerConfig"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.__init_once()
            return cls._instance

    def __init_once(self) -> None:
        self._configured = False
        self._qt_queue: Queue = Queue()
        self._last_fps_html: Optional[str] = None
        self._qt_widget = None
        self.app_name: str = "App"

    def configure(self, app_name: str, log_dir: Path) -> None:
        with self._lock:
            if self._configured:
                return
            self.app_name = app_name

            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
            log_file = log_dir / f"{timestamp}-logs.log"

            context_filter = _ContextFilter(app_name)

            root = logging.getLogger(app_name)
            root.setLevel(logging.DEBUG)
            root.propagate = False

            # Console
            console = logging.StreamHandler()
            console.addFilter(context_filter)
            console.setFormatter(_ColorFormatter())
            root.addHandler(console)

            # File
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.addFilter(context_filter)
            file_handler.setFormatter(_PlainFormatter())
            root.addHandler(file_handler)

            # Qt (always attached, drained only when widget is set)
            qt_handler = _QtQueueHandler(self._qt_queue)
            qt_handler.addFilter(context_filter)
            qt_handler.setFormatter(_PlainFormatter())
            root.addHandler(qt_handler)

            self._configured = True

    def attach_widget(self, widget) -> None:
        """Call from the GUI thread after the QTextEdit is ready."""
        self._qt_widget = widget

    def process_log_queue(self) -> None:
        """Drain the Qt queue — call this from a GUI timer."""
        if not self._qt_widget:
            return
        while not self._qt_queue.empty():
            try:
                html, is_fps = self._qt_queue.get_nowait()
                if is_fps and self._last_fps_html:
                    cursor = self._qt_widget.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    cursor.select(cursor.SelectionType.LineUnderCursor)
                    cursor.insertHtml(html)
                else:
                    self._qt_widget.append(html)
                if is_fps:
                    self._last_fps_html = html
                self._qt_widget.ensureCursorVisible()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def configure_logging(app_name: str, log_dir: Path) -> None:
    """Call once at startup before any Logger is created."""
    _RootLoggerConfig().configure(app_name, log_dir)


def attach_log_widget(widget) -> None:
    _RootLoggerConfig().attach_widget(widget)


def process_log_queue() -> None:
    _RootLoggerConfig().process_log_queue()


class Logger:
    """
    Thin wrapper around a stdlib logger.

    Usage:
        log = Logger("MyClass")
        log = Logger.for_class("MyClass")   # identical
        log.info("Hello")
    """

    def __init__(self, cls_name: str):
        self.cls_name = cls_name
        cfg = _RootLoggerConfig()
        app_name = getattr(cfg, "app_name", "App")
        self._log = logging.getLogger(f"{app_name}.{cls_name}")

    @classmethod
    def for_class(cls, name: str) -> "Logger":
        return cls(name)

    def debug(self, msg: str, *args) -> None:
        self._log.debug(msg, *args)

    def info(self, msg: str, *args) -> None:
        self._log.info(msg, *args)

    def warn(self, msg: str, *args) -> None:
        self._log.warning(msg, *args)

    def error(self, msg: str, *args) -> None:
        self._log.error(msg, *args)

    def critical(self, msg: str, *args) -> None:
        self._log.critical(msg, *args)
