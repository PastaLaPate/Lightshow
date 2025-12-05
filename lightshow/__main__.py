"""
Real-time audio spectrum visualization with kick detection.
"""

import sys
from typing import List
from pyaudio import PyAudio
from time import time_ns
import signal

import lightshow.utils.config as config
from lightshow.audio.processors import SpectrumProcessor
import lightshow.audio.detectors as detectors
from lightshow.audio.audio_streams import AudioStreamHandler, AudioListener
from lightshow.devices.device import PacketData, PacketStatus, PacketType
from lightshow.gui.main_window import UIManager
from lightshow.utils.tracks_infos import TracksInfoTracker
from lightshow.visualization.spike_detector_visualizer import SpikeDetectorVisualizer

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSession,
    GlobalSystemMediaTransportControlsSessionMediaProperties,
    GlobalSystemMediaTransportControlsSessionPlaybackInfo,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus,
)


class MainAudioListener(AudioListener):
    def __init__(self, AudioHandler: AudioStreamHandler):
        super().__init__(AudioHandler)
        # self.mh = MovingHead()
        self.kick_detector = detectors.KickDetector(AudioHandler)
        self.silent_detector = detectors.SilentDetector()
        self.break_detector = detectors.BreakDetector(30)
        self.drop_detector = detectors.DropDetector(30, 5)
        # Defer visualizer creation until a QApplication exists
        # (SpikeDetectorVisualizer is a QWidget and must be created after QApplication)
        self.kick_visualizer = None
        self.track_tracker = TracksInfoTracker()
        print("Adding track infos tracker")
        self.track_tracker.add_track_changed_listener(self.on_track_changed)
        self.track_tracker.add_playback_status_changed_listener(
            self.on_playback_status_changed
        )
        self.clear_state()

    def on_track_changed(
        self,
        session: GlobalSystemMediaTransportControlsSession,
        infos: GlobalSystemMediaTransportControlsSessionMediaProperties,
    ):
        print(f"Now playing {infos.title} ! (By {infos.artist})")
        self.send_packet_to_devices(PacketData(PacketType.NEW_MUSIC, PacketStatus.ON))
        self.clear_state()
        self.send_packet_to_devices(PacketData(PacketType.NEW_MUSIC, PacketStatus.OFF))

    def on_playback_status_changed(
        self,
        session: GlobalSystemMediaTransportControlsSession,
        status: GlobalSystemMediaTransportControlsSessionPlaybackInfo,
    ):
        ps = status.playback_status
        print(f"New status... {ps}")
        if ps == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED:
            self.music_paused = True
            self.paused_since = time_ns()
            self.send_packet_to_devices(PacketData(PacketType.BREAK, PacketStatus.ON))
        elif ps == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING:
            self.music_paused = False
            self.break_detector.clear_old_beats()
            self.break_detector.clean_beats(time_ns() - self.paused_since)
            self.send_packet_to_devices(PacketData(PacketType.BREAK, PacketStatus.OFF))
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
        if hasattr(self, "kick_detector"):
            self.kick_detector.clear()
            self.break_detector.clear()
            self.drop_detector.clear()
        # Only clear visualizer if it has been created (after QApplication exists)
        if hasattr(self, "kick_visualizer") and self.kick_visualizer:
            self.kick_visualizer.clear()

    def send_packet_to_devices(self, packet: PacketData):
        devices = (
            config.live_devices.copy()
        )  # Create copy to avoid exception during change
        for device in devices.values():
            if device.ready:
                device.on(packet)

    def __call__(self, data):
        self.send_packet_to_devices(PacketData(PacketType.TICK, PacketStatus.ON))
        if self.music_paused:
            return True

        beat = self.kick_detector.detect(
            data, appendCurrentEnergy=not self.break_detected
        )

        if beat:
            if self.break_detected:
                self.break_detected = False
                self.kick_detector.reset_state()
                self.break_detector.clear_old_beats()
                self.break_detector.clean_beats(
                    time_ns() - self.break_detector.beats[-1]
                )
                self.send_packet_to_devices(
                    PacketData(PacketType.BREAK, PacketStatus.OFF)
                )
            self.break_detector.on_beat()
            self.drop_detector.on_beat()
            self.send_packet_to_devices(PacketData(PacketType.BEAT, PacketStatus.ON))

        mbreak, drop = False, False
        if not self.break_detected and self.break_detector.detect(data):
            self.break_detected = True
            self.send_packet_to_devices(PacketData(PacketType.BREAK, PacketStatus.ON))
            mbreak = True
        if not self.drop_detected and self.drop_detector.detect(data):
            self.drop_detected = True
            self.send_packet_to_devices(PacketData(PacketType.DROP, PacketStatus.ON))
            drop = True
        if self.drop_detected and not self.drop_detector.detect(data):
            self.drop_detected = False
            self.send_packet_to_devices(PacketData(PacketType.DROP, PacketStatus.OFF))

        # Update visualizer data
        self.kick_visualizer(
            data, beat_detected=beat, break_detected=mbreak, drop_detected=drop
        )
        return True


def get_audio_devices() -> List[str]:
    """Returns a list of audio device names formatted for the combo box."""
    pyaudio_instance = PyAudio()
    devices = []
    for i in range(pyaudio_instance.get_device_count()):
        device_info = pyaudio_instance.get_device_info_by_index(i)
        devices.append(f"{i}: {device_info['name']}")
    pyaudio_instance.terminate()
    return devices


def main():
    global ui_manager
    from PyQt6.QtWidgets import QApplication

    audio_devices = get_audio_devices()

    # The AudioStreamHandler is now initialized but not started.
    # The UIManager will control when the stream starts and stops.
    audio_handler = AudioStreamHandler(SpectrumProcessor, config.global_config)
    listener = MainAudioListener(audio_handler)
    audio_handler.add_listener_on_init(listener)

    # Create Qt application
    app = QApplication(sys.argv)

    # Now that a QApplication exists, create the visualizer QWidget
    # and attach it to the listener. The visualizer depends on Qt widgets.
    listener.kick_visualizer = SpikeDetectorVisualizer(listener.kick_detector)

    # Create and show the GUI, passing all necessary components
    ui_manager = UIManager(listener, audio_handler, config.global_config, audio_devices)
    ui_manager.show()

    # Run the application
    sys.exit(app.exec())


def terminate(sig, frame):
    print("Interrupt signal caught! Stopping gracefully...")
    try:
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
            ui_manager.stop()
        except Exception:
            pass
        sys.exit(0)
