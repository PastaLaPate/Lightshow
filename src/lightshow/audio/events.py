from PySide6.QtCore import QObject, Signal


class AudioEvents(QObject):
    streaming_status_changed = Signal(
        bool
    )  # True if stream is started False if stopped


audio_events = AudioEvents()
