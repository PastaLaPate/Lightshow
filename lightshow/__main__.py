import os
import signal
import sys
from time import time_ns

import pyqtgraph as pg
from PyQt6.QtCore import QObject, pyqtSignal

import lightshow.audio.detectors as detectors
import lightshow.utils.config as config
from lightshow.audio.audio_streams import (
    AAudioStreamHandler,
    AudioListener,
    LoopbackAudioStreamHandler,
)
from lightshow.audio.processors import SpectrumProcessor
from lightshow.devices.device import PacketData, PacketStatus, PacketType
from lightshow.gui.main_window import UIManager
from lightshow.utils import Logger, TracksInfoTracker
from lightshow.utils.config import resource_path
from lightshow.utils.tracks_infos import PlaybackInfo, TrackInfo
from lightshow.visualization.frequencies_visualizer import FrequenciesVisualizer
from lightshow.visualization.spike_detector_visualizer import SpikeDetectorVisualizer

pg.setConfigOptions(useOpenGL=True, enableExperimental=True)

ui_manager: "UIManager | None" = None


class GuiBridge(QObject):
    clear_visualizer_signal = pyqtSignal()


class MainAudioListener(AudioListener):
    def __init__(self, AudioHandler: AAudioStreamHandler):
        super().__init__(AudioHandler)
        self.logger = Logger("AudioListener")
        self.kick_detector = detectors.KickDetector(AudioHandler)
        self.silent_detector = detectors.SilentDetector()
        self.break_detector = detectors.BreakDetector(30)
        self.drop_detector = detectors.DropDetector(30, 5)
        self.kick_visualizer: SpikeDetectorVisualizer | None = None
        self.freq_visualizer: FrequenciesVisualizer | None = None
        self.gui_bridge = GuiBridge()
        self.track_tracker = TracksInfoTracker()
        self.logger.info("Adding track infos tracker")
        self.track_tracker.add_track_changed_listener(self.on_track_changed)
        self.track_tracker.add_playback_status_changed_listener(
            self.on_playback_status_changed
        )
        self.clear_state()

    def changed_visualizer_settings(self) -> None:
        if hasattr(self, "kick_visualizer") and self.kick_visualizer:
            self.gui_bridge.clear_visualizer_signal.connect(self.kick_visualizer.clear)

    def on_track_changed(self, player_name: str, infos: TrackInfo) -> None:
        if infos.title:
            self.logger.info(f"Now playing {infos.title} ! (By {infos.artist})")
            self.send_packet_to_devices(
                PacketData(PacketType.NEW_MUSIC, PacketStatus.ON)
            )
            self.clear_state()
            self.send_packet_to_devices(
                PacketData(PacketType.NEW_MUSIC, PacketStatus.OFF)
            )

    def on_playback_status_changed(
        self, player_name: str, status: PlaybackInfo
    ) -> None:
        self.logger.info(f"New playback status: {status.playback_status}")

        if status.playback_status == "paused":
            self.music_paused = True
            self.paused_since = time_ns()
            self.send_packet_to_devices(PacketData(PacketType.BREAK, PacketStatus.ON))

        elif status.playback_status == "playing":
            self.music_paused = False
            self.break_detector.clear_old_beats()
            self.break_detector.clean_beats(time_ns() - self.paused_since)
            self.send_packet_to_devices(PacketData(PacketType.BREAK, PacketStatus.OFF))
            self.paused_since = 0

        # "stopped" requires no action beyond the log above

    def clear_state(self) -> None:
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
        self.power_decay_time = 0.5  # Decay power over 0.5 seconds
        if hasattr(self, "kick_detector"):
            self.kick_detector.clear()
            self.break_detector.clear()
            self.drop_detector.clear()
        if hasattr(self, "kick_visualizer") and self.kick_visualizer:
            self.gui_bridge.clear_visualizer_signal.emit()
        if isinstance(self.stream_handler, LoopbackAudioStreamHandler):
            try:
                if self.stream_handler.audio_capture:
                    self.stream_handler.audio_capture.audio_buffer.clear()
                    self.stream_handler.audio_capture.sample_queue.queue.clear()
            except Exception:
                pass

    def send_packet_to_devices(self, packet: PacketData) -> None:
        devices = config.live_devices.copy()
        for device in devices.values():
            if device.ready:
                device.on(packet)

    def set_beat_power(self, beat_intensity: float) -> None:
        """
        Set power based on beat intensity.
        beat_intensity: should be between 0 and 1 (normalized).
        """
        self.current_power = int(beat_intensity * 100)
        self.power_since = time_ns()

    def get_current_power(self) -> int:
        """
        Calculate power with exponential decay over time.
        Returns power value between 0 and 100.
        """
        if self.current_power <= 0:
            return 0

        time_elapsed = (time_ns() - self.power_since) / 1e9
        decay_factor = 2.71828 ** (-time_elapsed / self.power_decay_time)
        power = int(self.current_power * decay_factor)

        if power < 1:
            self.current_power = 0
            return 0
        return power

    def __call__(self, data) -> bool:
        current_power = self.get_current_power()
        self.send_packet_to_devices(
            PacketData(
                PacketType.TICK, PacketStatus.ON, audio_data=data, power=current_power
            )
        )
        if self.freq_visualizer:
            self.freq_visualizer(data)
        if self.music_paused:
            return True

        beat = self.kick_detector.detect(
            data, appendCurrentEnergy=not self.break_detected
        )

        if beat:
            try:
                bass_energy = data.frequencies[0]
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
        if self.kick_visualizer:
            self.kick_visualizer(
                data, beat_detected=beat, break_detected=mbreak, drop_detected=drop
            )
        return True


def main() -> None:
    global ui_manager
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    audio_handler = LoopbackAudioStreamHandler(SpectrumProcessor, config.global_config)
    listener = MainAudioListener(audio_handler)
    audio_handler.add_listener_on_init(listener)

    app = QApplication(sys.argv)
    app.setApplicationName("lightshow")

    if os.name == "nt":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "pastalapate.lightshow"
        )

    ICON_PATH = resource_path("lightshow/gui/assets/lightshow_icon.png")
    icon = QIcon(ICON_PATH)
    app.setWindowIcon(icon)

    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    listener.kick_visualizer = SpikeDetectorVisualizer(listener.kick_detector)
    listener.freq_visualizer = FrequenciesVisualizer()
    listener.changed_visualizer_settings()

    ui_manager = UIManager(listener, audio_handler)
    ui_manager.setProperty("_NET_WM_NAME", "Lightshow")
    ui_manager.resize(800, 600)
    listener.track_tracker.start()
    ui_manager.show()
    ui_manager.setWindowIcon(QIcon(ICON_PATH))

    sys.exit(app.exec())


def terminate(sig: int, frame: object) -> None:
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
