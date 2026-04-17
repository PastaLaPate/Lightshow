import os
import signal
import sys
from time import time_ns
from typing import Any, List

import pyqtgraph as pg
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal

import lightshow.audio.detectors as detectors
import lightshow.utils.config as config
from lightshow.audio.audio_streams import AudioListener, AudioStreamHandler
from lightshow.audio.processors import SpectrumProcessor
from lightshow.devices.device import PacketData, PacketStatus, PacketType
from lightshow.gui.main_window import UIManager
from lightshow.utils import Logger, TracksInfoTracker
from lightshow.utils.config import resource_path
from lightshow.visualization.spike_detector_visualizer import SpikeDetectorVisualizer

if os.name == "nt":
    try:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSession,
            GlobalSystemMediaTransportControlsSessionMediaProperties,
            GlobalSystemMediaTransportControlsSessionPlaybackInfo,
            GlobalSystemMediaTransportControlsSessionPlaybackStatus,
        )

        WINRT_AVAILABLE = True
    except Exception:
        WINRT_AVAILABLE = False
        GlobalSystemMediaTransportControlsSession = Any
        GlobalSystemMediaTransportControlsSessionMediaProperties = Any
        GlobalSystemMediaTransportControlsSessionPlaybackInfo = Any
        GlobalSystemMediaTransportControlsSessionPlaybackStatus = None
else:
    WINRT_AVAILABLE = False
    GlobalSystemMediaTransportControlsSession = Any
    GlobalSystemMediaTransportControlsSessionMediaProperties = Any
    GlobalSystemMediaTransportControlsSessionPlaybackInfo = Any
    GlobalSystemMediaTransportControlsSessionPlaybackStatus = None
pg.setConfigOptions(useOpenGL=True, enableExperimental=True)

ui_manager = None


class GuiBridge(QObject):
    clear_visualizer_signal = pyqtSignal()


class MainAudioListener(AudioListener):
    def __init__(self, AudioHandler: AudioStreamHandler):
        super().__init__(AudioHandler)
        self.logger = Logger("AudioListener")
        self.kick_detector = detectors.KickDetector(AudioHandler)
        self.silent_detector = detectors.SilentDetector()
        self.break_detector = detectors.BreakDetector(30)
        self.drop_detector = detectors.DropDetector(30, 5)
        self.kick_visualizer: SpikeDetectorVisualizer | None = None
        self.gui_bridge = GuiBridge()
        self.track_tracker = TracksInfoTracker()
        self.logger.info("Adding track infos tracker")
        self.track_tracker.add_track_changed_listener(self.on_track_changed)
        self.track_tracker.add_playback_status_changed_listener(
            self.on_playback_status_changed
        )
        self.clear_state()

    def changed_visualizer_settings(self):
        if hasattr(self, "kick_visualizer") and self.kick_visualizer:
            self.gui_bridge.clear_visualizer_signal.connect(self.kick_visualizer.clear)

    def on_track_changed(
        self,
        session: Any,
        infos: Any,
    ):
        # If winrt is available, infos will typically have title/artist attributes.
        title = getattr(infos, "title", None)
        artist = getattr(infos, "artist", None)
        if title:
            self.logger.info(f"Now playing {title} ! (By {artist})")
            self.send_packet_to_devices(
                PacketData(PacketType.NEW_MUSIC, PacketStatus.ON)
            )
            self.clear_state()
            self.send_packet_to_devices(
                PacketData(PacketType.NEW_MUSIC, PacketStatus.OFF)
            )

    def on_playback_status_changed(
        self,
        session: Any,
        status: Any,
    ):
        ps = getattr(status, "playback_status", None)
        self.logger.info(f"New playback status : {ps}")

        # Handle WinRT enum values when available, else support simple string values
        if (
            WINRT_AVAILABLE
            and GlobalSystemMediaTransportControlsSessionPlaybackStatus is not None
        ):
            if ps == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED:
                self.music_paused = True
                self.paused_since = time_ns()
                self.send_packet_to_devices(
                    PacketData(PacketType.BREAK, PacketStatus.ON)
                )
            elif ps == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
                self.music_paused = False
                self.break_detector.clear_old_beats()
                self.break_detector.clean_beats(time_ns() - self.paused_since)
                self.send_packet_to_devices(
                    PacketData(PacketType.BREAK, PacketStatus.OFF)
                )
                self.paused_since = 0
        else:
            # Some platforms may provide simple string statuses; be permissive.
            if isinstance(ps, str) and ps.lower() == "paused":
                self.music_paused = True
                self.paused_since = time_ns()
                self.send_packet_to_devices(
                    PacketData(PacketType.BREAK, PacketStatus.ON)
                )
            elif isinstance(ps, str) and ps.lower() in ("playing", "play"):
                self.music_paused = False
                self.break_detector.clear_old_beats()
                self.break_detector.clean_beats(time_ns() - self.paused_since)
                self.send_packet_to_devices(
                    PacketData(PacketType.BREAK, PacketStatus.OFF)
                )
                self.paused_since = 0

    def clear_state(self):
        """Resets all detectors and visualizers to their initial state."""
        self.break_detected = False
        self.drop_detected = False
        self.silence_detected = False
        self.silence_since = 0
        self.new_music = False
        self.music_paused = False
        self.paused_since = 0
        self.current_power = 0
        self.power_since = 0
        self.power_decay_time = 0.5  # Decay power over 0.5 seconds (in seconds)
        if hasattr(self, "kick_detector"):
            self.kick_detector.clear()
            self.break_detector.clear()
            self.drop_detector.clear()
        # Only clear visualizer if it has been created (after QApplication exists)
        if hasattr(self, "kick_visualizer") and self.kick_visualizer:
            self.gui_bridge.clear_visualizer_signal.emit()

    def send_packet_to_devices(self, packet: PacketData):
        devices = (
            config.live_devices.copy()
        )  # Create copy to avoid exception during change
        for device in devices.values():
            if device.ready:
                device.on(packet)

    def set_beat_power(self, beat_intensity: float):
        """
        Set power based on beat intensity.
        beat_intensity: should be between 0 and 1 (normalized)
        """
        self.current_power = int(beat_intensity * 100)  # Scale to 0-100
        self.power_since = time_ns()

    def get_current_power(self) -> int:
        """
        Calculate power with exponential decay over time.
        Returns power value between 0 and 100.
        """
        if self.current_power <= 0:
            return 0

        time_elapsed = (time_ns() - self.power_since) / 1e9  # Convert ns to seconds

        # Exponential decay: power = max_power * e^(-time/decay_time)
        decay_factor = 2.71828 ** (-time_elapsed / self.power_decay_time)
        power = int(self.current_power * decay_factor)

        if power < 1:
            self.current_power = 0
            return 0
        return power

    def __call__(self, data):
        current_power = self.get_current_power()
        self.send_packet_to_devices(
            PacketData(
                PacketType.TICK, PacketStatus.ON, audio_data=data, power=current_power
            )
        )
        if self.music_paused:
            return True

        beat = self.kick_detector.detect(
            data, appendCurrentEnergy=not self.break_detected
        )

        if beat:
            # Calculate beat intensity from frequency data (0-100 scale)
            # Using bass frequencies (0-40) which are analyzed by kick detector
            try:
                bass_energy = data.get_freq_mean([0, 40])
                # Normalize to 0-1 range (adjust max based on your typical max energy)
                beat_intensity = min(bass_energy / 1e13, 1.0)
            except Exception:
                beat_intensity = 1.0

            self.set_beat_power(beat_intensity)

            if self.break_detected:
                self.break_detected = False
                self.kick_detector.reset_state()
                self.break_detector.clear_old_beats()
                self.break_detector.clean_beats(
                    time_ns() - self.break_detector.beats[-1]
                )
                self.send_packet_to_devices(
                    PacketData(PacketType.BREAK, PacketStatus.OFF, audio_data=data)
                )
            self.break_detector.on_beat()
            self.drop_detector.on_beat()
            self.send_packet_to_devices(
                PacketData(
                    PacketType.BEAT,
                    PacketStatus.ON,
                    audio_data=data,
                    power=self.current_power,
                )
            )

        mbreak, drop = False, False
        if not self.break_detected and self.break_detector.detect(data):
            self.break_detected = True
            self.send_packet_to_devices(
                PacketData(PacketType.BREAK, PacketStatus.ON, audio_data=data)
            )
            mbreak = True
        if not self.drop_detected and self.drop_detector.detect(data):
            self.drop_detected = True
            self.send_packet_to_devices(
                PacketData(PacketType.DROP, PacketStatus.ON, audio_data=data)
            )
            drop = True
        if self.drop_detected and not self.drop_detector.detect(data):
            self.drop_detected = False
            self.send_packet_to_devices(
                PacketData(PacketType.DROP, PacketStatus.OFF, audio_data=data)
            )
        # Update visualizer data
        if self.kick_visualizer:
            self.kick_visualizer(
                data, beat_detected=beat, break_detected=mbreak, drop_detected=drop
            )
        return True


def get_audio_devices() -> List[str]:
    """Returns a list of audio device names formatted for the combo box."""
    try:
        devices = []
        device_count = sd.query_devices(kind="input")
        if isinstance(device_count, dict):
            # Single device case
            devices.append(f"{0}: {device_count['name']}")
        else:
            # Multiple devices
            for i, device in enumerate(device_count):
                if device["max_input_channels"] > 0:
                    devices.append(f"{i}: {device['name']}")
        return devices
    except Exception:
        # If device enumeration fails, return empty list
        return []


def main():
    global ui_manager
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    audio_devices = get_audio_devices()

    # The AudioStreamHandler is now initialized but not started.
    # The UIManager will control when the stream starts and stops.
    audio_handler = AudioStreamHandler(SpectrumProcessor, config.global_config)
    listener = MainAudioListener(audio_handler)
    audio_handler.add_listener_on_init(listener)

    # Create Qt application
    app = QApplication(sys.argv)

    if os.name == "nt":
        # Workaround to set app user model id on Windows for proper taskbar icon display
        import ctypes

        myappid = "pastalapate.lightshow"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    ICON_PATH = resource_path("lightshow/gui/assets/lightshow_icon.png")
    app.setWindowIcon(QIcon(ICON_PATH))
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    # Now that a QApplication exists, create the visualizer QWidget
    # and attach it to the listener. The visualizer depends on Qt widgets.
    listener.kick_visualizer = SpikeDetectorVisualizer(listener.kick_detector)
    listener.changed_visualizer_settings()

    # Create and show the GUI, passing all necessary components
    ui_manager = UIManager(listener, audio_handler, config.global_config, audio_devices)
    ui_manager.setWindowIcon(QIcon(ICON_PATH))
    ui_manager.resize(800, 600)
    ui_manager.show()

    # Run the application
    sys.exit(app.exec())


def terminate(sig, frame):
    print("Interrupt signal caught! Stopping gracefully...")
    try:
        if ui_manager:
            ui_manager.stop()
    except Exception as e:
        print(f"Error during shutdown: {e}")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, terminate)
    try:
        main()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt caught, exiting...")
        try:
            if ui_manager:
                ui_manager.stop()
        except Exception:
            pass
        sys.exit(0)
