from PyQt6.QtCore import QObject, pyqtSignal


class UISignals(QObject):
    """Signals for thread-safe communication with UI."""

    finish_connection = pyqtSignal(str)
    show_error = pyqtSignal(str, str)
    show_info = pyqtSignal(str, str)
    connection_status_changed = pyqtSignal(str)
    streaming_status_changed = pyqtSignal(bool)


ui_signals = UISignals()
