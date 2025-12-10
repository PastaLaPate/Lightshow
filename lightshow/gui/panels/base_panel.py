import traceback

from PySide6.QtWidgets import QVBoxLayout, QWidget


class BasePanel(QWidget):
    """Base class for all UI panels with callback support."""

    def __init__(self):
        super().__init__()
        self._callbacks = {}

    def register(self, event: str, callback):
        """Register a callback for a named event."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def trigger(self, event: str, *args, **kwargs):
        """Trigger all callbacks registered for an event."""
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception:
                traceback.print_exc()

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create Qt UI elements. Override in subclasses."""
        pass
        pass
        pass
