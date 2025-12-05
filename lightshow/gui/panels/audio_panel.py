import threading
from typing import List

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel

from .base_panel import BasePanel
from lightshow.utils.config import Config
from lightshow.audio.audio_streams import AudioStreamHandler


class AudioPanel(BasePanel):
    """Panel for audio stream control and visualization."""

    def __init__(
        self,
        listener,
        audio_handler: AudioStreamHandler,
        config: Config,
        audio_devices: List[str],
    ):
        super().__init__()
        self.listener = listener
        self.audio_handler = audio_handler
        self.config = config
        self.audio_devices = audio_devices.copy()
        self.audio_devices.append("-1: Autodetect used device")
        self.is_streaming = False
        self.audio_thread: threading.Thread | None = None

        # UI Elements
        self.stream_button = None
        self.device_combo = None
        self.visualizer = None

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the audio panel UI elements."""
        # Title
        title_label = QLabel("Audio")
        layout.addWidget(title_label)

        # Control buttons and combo
        controls_layout = QHBoxLayout()

        self.stream_button = QPushButton("Start Stream")
        self.stream_button.clicked.connect(self._stream_button_callback)
        controls_layout.addWidget(self.stream_button)

        device_label = QLabel("Audio Device:")
        controls_layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.addItems(self.audio_devices)
        # Set default value
        default_device = next(
            (
                d
                for d in self.audio_devices
                if d.startswith(str(self.config.device_index))
            ),
            "",
        )
        if default_device:
            self.device_combo.setCurrentText(default_device)
        self.device_combo.currentTextChanged.connect(self._device_selection_callback)
        controls_layout.addWidget(self.device_combo)

        layout.addLayout(controls_layout)

        # Add spike detector visualizer from listener
        if self.listener and hasattr(self.listener, "kick_visualizer"):
            self.visualizer = self.listener.kick_visualizer
            layout.addWidget(self.visualizer, 1)

        layout.addStretch()

    def _stream_button_callback(self):
        """Handle stream button clicks."""
        if not self.is_streaming:
            self.trigger("start_stream")
        else:
            self.trigger("stop_stream")

    def set_streaming(self, value: bool):
        """Update streaming state and UI."""
        self.is_streaming = value
        self.stream_button.setText("Stop Stream" if value else "Start Stream")
        self.device_combo.setEnabled(not value)

    def _device_selection_callback(self):
        """Handle audio device selection."""
        try:
            app_data = self.device_combo.currentText()
            self.config.device_index = int(app_data.split(":")[0])
            self.trigger("device_changed", app_data)
        except Exception:
            pass
