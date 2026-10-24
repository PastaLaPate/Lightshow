import threading
from typing import Any

import soundcard
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from lightshow.audio.events import audio_events
from lightshow.audio.streams import AAudioStreamHandler
from lightshow.audio.types import AudioDevice
from lightshow.core.config import _Settings, global_config
from lightshow.core.logger import Logger
from lightshow.gui.panels.logs import Logs
from lightshow.gui.theme import style
from lightshow.gui.utils import ui_signals

from .base_panel import BasePanel

logger = Logger.for_class("AudioPanel")


class AudioPanel(BasePanel):
    """Panel for audio stream control and visualization."""

    def __init__(
        self,
        listener,
        audio_handler: AAudioStreamHandler,
    ):
        super().__init__()

        self.listener = listener

        listener.track_tracker.add_track_changed_listener(self._on_track_changed)

        self.audio_handler = audio_handler
        self.audio_devices: dict[
            str, dict
        ] = {}  # Name -> Serialized device info (id, is_loopback, etc)

        self.is_streaming = False
        self.audio_thread: threading.Thread | None = None

        # UI Elements
        self.stream_button = None
        self.device_combo = None
        self.playing_label = None
        self.kick_visualizer = None
        self.spectrumWidget = QWidget()
        self.logs = Logs()

        audio_events.streaming_status_changed.connect(self._on_stream_status_changed)
        ui_signals.settings.changed.connect(self._on_settings_changed)

        self.fetch_audio_devices()

    def fetch_audio_devices(self):
        self.audio_devices.clear()
        self.audio_devices["Autodetect used speaker"] = AudioDevice(
            is_default=True, is_loopback=True
        ).to_dict()

        recordable_mics = soundcard.all_microphones(include_loopback=True)
        recordable_speakers = [d for d in recordable_mics if d.isloopback]

        for speaker in recordable_speakers:
            self.audio_devices[f"[Loopback] {speaker.name}"] = AudioDevice(
                name=speaker.name, is_default=False, is_loopback=True
            ).to_dict()

        self.audio_devices["Autodetect default input (mic)"] = AudioDevice(
            is_default=True, is_loopback=False
        ).to_dict()

        for mic in soundcard.all_microphones(include_loopback=False):
            self.audio_devices[mic.name] = AudioDevice(
                name=mic.name, is_default=False, is_loopback=False
            ).to_dict()

    def create_qt_ui(self, layout: QVBoxLayout):
        """Create the audio panel UI elements."""
        # Title
        topWidget = QWidget()
        self.topLayout = QVBoxLayout(topWidget)
        title_label = QLabel("Audio")
        style.mark(title_label, "heading")
        self.topLayout.addWidget(title_label)

        # Control buttons and combo
        controls_layout = QHBoxLayout()

        self.stream_button = QPushButton("Start Stream")
        self.stream_button.clicked.connect(self._stream_button_callback)
        controls_layout.addWidget(self.stream_button)

        device_label = QLabel("Audio Device:")
        controls_layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.addItems(list(self.audio_devices.keys()))
        try:
            keys = list(self.audio_devices.keys())
            values = list(self.audio_devices.values())
            selected_device = keys[values.index(global_config.audio_device.to_dict())]
            if selected_device:
                self.device_combo.setCurrentText(selected_device)
        except KeyError:
            logger.warning(
                "Failed to set audio device combo to saved config value, defaulting to first option."
            )
            self.device_combo.setCurrentIndex(0)
        self.device_combo.currentTextChanged.connect(self._device_selection_callback)
        controls_layout.addWidget(self.device_combo)

        self.topLayout.addLayout(controls_layout)

        self.playing_label = QLabel("No track playing")
        self.topLayout.addWidget(self.playing_label)

        self.spectrumLayout = QVBoxLayout(self.spectrumWidget)

        # Add spike detector visualizer from listener
        if self.listener and hasattr(self.listener, "kick_visualizer"):
            self.kick_visualizer = self.listener.kick_visualizer
            self.topLayout.addWidget(self.kick_visualizer, 1)
        if self.listener and hasattr(self.listener, "freq_visualizer"):
            self.freq_visualizer = self.listener.freq_visualizer
            self.spectrumLayout.addWidget(self.freq_visualizer, 1)

        logsWidget = QWidget()
        logs_layout = QVBoxLayout(logsWidget)
        self.logs.create_qt_ui(logs_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(topWidget)
        splitter.addWidget(self.spectrumWidget)
        splitter.addWidget(logsWidget)
        splitter.setStretchFactor(0, 50)
        splitter.setStretchFactor(1, 20)
        splitter.setStretchFactor(2, 30)
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
            ui_signals.audio_req.start_stream.emit()
        else:
            ui_signals.audio_req.stop_stream.emit()

    def _on_stream_status_changed(self, status: bool):
        self.is_streaming = status
        if self.stream_button and self.device_combo:
            self.stream_button.setText("Stop Stream" if status else "Start Stream")
            self.device_combo.setEnabled(not status)

    def _device_selection_callback(self):
        """Handle audio device selection."""
        try:
            if self.device_combo:
                app_data = self.device_combo.currentText()
                ui_signals.audio_req.set_device.emit(
                    AudioDevice.from_dict(self.audio_devices[app_data])
                )
        except Exception as e:  # noqa
            logger.error(str(e))

    def _on_track_changed(
        self,
        session,
        infos,
    ):
        if self.playing_label:
            self.playing_label.setText(f"Playing: {infos.title} - {infos.artist}")

    def _on_settings_changed(self, changed_settings: dict[str, Any]):
        if _Settings.SHOW_SPECTRUM.id in changed_settings:
            if changed_settings[_Settings.SHOW_SPECTRUM.id]:
                self.spectrumWidget.show()
            else:
                self.spectrumWidget.hide()

        if _Settings.SHOW_BEAT_DETECTION.id in changed_settings:
            w = self.kick_visualizer
            if isinstance(w, QWidget):
                if changed_settings[_Settings.SHOW_BEAT_DETECTION.id]:
                    w.show()
                else:
                    w.hide()
