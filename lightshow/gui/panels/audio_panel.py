import threading

import soundcard
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from lightshow.audio.audio_streams import AAudioStreamHandler
from lightshow.gui.components.logs import Logs
from lightshow.utils.config import Config

from .base_panel import BasePanel


class AudioPanel(BasePanel):
    """Panel for audio stream control and visualization."""

    def __init__(
        self,
        listener,
        audio_handler: AAudioStreamHandler,
        config: Config,
    ):
        super().__init__()
        self.listener = listener
        listener.track_tracker.add_track_changed_listener(self.on_track_changed)
        self.audio_handler = audio_handler
        self.config = config
        self.audio_devices = {}
        self.audio_devices["Autodetect used speaker"] = soundcard.default_speaker().id
        recordable_mics = soundcard.all_microphones(include_loopback=True)
        recordable_speakers = [d for d in recordable_mics if d.isloopback]
        for speaker in recordable_speakers:
            self.audio_devices[speaker.name] = speaker.id
        self.audio_devices["Autodetect default input (mic)"] = (
            soundcard.default_microphone().id
        )
        for mic in soundcard.all_microphones(include_loopback=False):
            self.audio_devices[mic.name] = mic.id
        self.is_streaming = False
        self.audio_thread: threading.Thread | None = None

        # UI Elements
        self.stream_button = None
        self.device_combo = None
        self.playing_label = None
        self.kick_visualizer = None
        self.logs = Logs()

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the audio panel UI elements."""
        # Title
        topWidget = QWidget()
        topLayout = QVBoxLayout(topWidget)
        title_label = QLabel("Audio")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        topLayout.addWidget(title_label)

        # Control buttons and combo
        controls_layout = QHBoxLayout()

        self.stream_button = QPushButton("Start Stream")
        self.stream_button.clicked.connect(self._stream_button_callback)
        controls_layout.addWidget(self.stream_button)

        device_label = QLabel("Audio Device:")
        controls_layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.addItems(self.audio_devices.keys())
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

        topLayout.addLayout(controls_layout)

        self.playing_label = QLabel("No track playing")
        topLayout.addWidget(self.playing_label)

        # Add spike detector visualizer from listener
        if self.listener and hasattr(self.listener, "kick_visualizer"):
            self.kick_visualizer = self.listener.kick_visualizer
            topLayout.addWidget(self.kick_visualizer, 1)
        if self.listener and hasattr(self.listener, "freq_visualizer"):
            self.freq_visualizer = self.listener.freq_visualizer
            topLayout.addWidget(self.freq_visualizer, 1)

        logsWidget = QWidget()
        logs_layout = QVBoxLayout(logsWidget)
        self.logs.create_qt_ui(logs_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(topWidget)
        splitter.addWidget(logsWidget)
        splitter.setStretchFactor(0, 70)
        splitter.setStretchFactor(1, 30)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #333;
            }                       
        """
        )

        layout.addWidget(splitter)

    def _stream_button_callback(self):
        """Handle stream button clicks."""
        if not self.is_streaming:
            self.trigger("start_stream")
        else:
            self.trigger("stop_stream")

    def set_streaming(self, value: bool):
        """Update streaming state and UI."""
        self.is_streaming = value
        if self.stream_button and self.device_combo:
            self.stream_button.setText("Stop Stream" if value else "Start Stream")
            self.device_combo.setEnabled(not value)

    def _device_selection_callback(self):
        """Handle audio device selection."""
        try:
            if self.device_combo:
                app_data = self.device_combo.currentText()
                # self.config.device_index = self.audio_devices[app_data]
                self.trigger("device_changed", self.audio_devices[app_data])
        except Exception:
            pass

    def on_track_changed(
        self,
        session,
        infos,
    ):
        if self.playing_label:
            self.playing_label.setText(f"Playing: {infos.title} - {infos.artist}")
