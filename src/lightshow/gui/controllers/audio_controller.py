import traceback

from PySide6.QtCore import QObject

from lightshow.audio.types import AAudioStreamHandler, AudioDevice
from lightshow.core.config import global_config
from lightshow.gui.utils import ui_signals


class AudioController(
    QObject,
):
    def __init__(self, listener, audio_handler: AAudioStreamHandler) -> None:
        super().__init__(None)

        self.listener = listener
        self.audio_handler = audio_handler

        ui_signals.audio_req.start_stream.connect(self._on_start_stream)
        ui_signals.audio_req.stop_stream.connect(self._on_stop_stream)
        ui_signals.audio_req.set_device.connect(self.set_audio_device)

    def _on_start_stream(self):
        """Start audio stream."""
        try:
            self.audio_handler.reinit_stream()
            self.listener.clear_state()
        except Exception as e:  # noqa
            ui_signals.dialogs.show_error.emit(
                "Streaming Error",
                f"Failed to start audio stream:\n\n{traceback.format_exc()}",
            )
            ui_signals.audio.streaming_status_changed.emit(False)

    def _on_stop_stream(self):
        """Stop audio stream."""
        self.audio_handler.stop_stream()

    def set_audio_device(self, device: AudioDevice):
        global_config.audio_device = device
