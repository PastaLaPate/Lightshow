import datetime
import os
from pathlib import Path
import threading
from queue import Queue
from PyQt6.QtWidgets import QTextEdit


class LoggerCore:
    """Singleton backend that writes to file, console, and QTextEdit."""

    _instance = None
    _lock = threading.Lock()

    COLORS = {
        "DEBUG": "#9b9b9b",
        "INFO": "#00ccff",
        "WARN": "#ffcc00",
        "ERROR": "#ff4444",
    }

    ANSI = {
        "DEBUG": "\033[90m",
        "INFO": "\033[96m",
        "WARN": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m",
    }

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_logger()
            return cls._instance

    def _init_logger(self):
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        self.filename = (
            Path(os.getenv("LOCALAPPDATA") or ".\\")
            / ".LightShow"
            / f"{timestamp}-logs.log"
        )
        self.file = open(self.filename, "a", encoding="utf-8")
        self.qt_widget = None
        self.log_queue = Queue()
        self.last_fps_html = None  # Track last FPS message for replacement

    def attach_widget(self, widget: QTextEdit):
        self.qt_widget = widget

    def emit(self, level, cls_name, message):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        base = f"{now} [Lightshow] [{cls_name}] [{level}] : {message}"

        # Console
        print(f"{self.ANSI[level]}{base}{self.ANSI['RESET']}")

        # File
        self.file.write(base + "\n")
        self.file.flush()

        # GUI - queue message instead of blocking
        if self.qt_widget:
            gui_color = self.COLORS[level]
            html = f'<span style="color:{gui_color}">{base}</span>'

            # If this is an FPS message, mark it for replacement
            is_fps = "Average fps" in message
            self.log_queue.put((html, is_fps))

    def process_log_queue(self):
        """Call this from the GUI thread to process queued log messages."""
        if not self.qt_widget:
            return

        # Process all queued messages
        while not self.log_queue.empty():
            try:
                item = self.log_queue.get_nowait()
                html, is_fps = item if isinstance(item, tuple) else (item, False)

                if is_fps and self.last_fps_html:
                    # Replace the last FPS line instead of adding a new one
                    doc = self.qt_widget.document()
                    cursor = self.qt_widget.textCursor()
                    # Move to end and select the last line
                    cursor.movePosition(cursor.MoveOperation.End)
                    cursor.select(cursor.SelectionType.LineUnderCursor)
                    cursor.insertHtml(html)
                else:
                    self.qt_widget.append(html)

                if is_fps:
                    self.last_fps_html = html
                self.qt_widget.ensureCursorVisible()
            except:
                break


class Logger:
    """
    Lightweight wrapper that holds the class name.
    Usage:
        log = Logger.for_class("MyClass")
        log.info("Hello")
    """

    def __init__(self, cls_name):
        self.cls_name = cls_name
        self.core = LoggerCore()

    @classmethod
    def for_class(cls, name):
        return Logger(name)

    def debug(self, msg):
        self.core.emit("DEBUG", self.cls_name, msg)

    def info(self, msg):
        self.core.emit("INFO", self.cls_name, msg)

    def warn(self, msg):
        self.core.emit("WARN", self.cls_name, msg)

    def error(self, msg):
        self.core.emit("ERROR", self.cls_name, msg)
