from PySide6.QtCore import QObject, Signal


class Notifications(QObject):
    error = Signal(str, str)  # title, content
    info = Signal(str, str)  # title, content


notifications = Notifications()
