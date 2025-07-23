"""
Real-time audio spectrum visualization with kick detection.
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation

from pyaudio import PyAudio, paWASAPI

from config import Config
from audio.processors import SpectrumProcessor
import audio.effects as effects
from audio.audio_streams import AudioStreamHandler, AudioListener
from visualization.spike_detector_visualizer import SpikeDetectorVisualizer
from devices.moving_head import MovingHead
from devices.device import PacketData, PacketStatus, PacketType
from time import time_ns

plt.style.use("dark_background")


class MainAudioListener(AudioListener):
    def __init__(self, channels, chunk_size, sample_rate, ax_kick):
        super().__init__(channels, chunk_size, sample_rate)
        self.mh = MovingHead()
        self.kick_detector = effects.KickDetector(int(sample_rate / chunk_size))
        self.silent_detector = effects.SilentDetector()
        self.break_detector = effects.BreakDetector(30)
        self.drop_detector = effects.DropDetector(30, 5)  # Maybe needs to be fine-tuned
        self.kick_visualizer = SpikeDetectorVisualizer(self.kick_detector, ax_kick)
        self.break_detected = False
        self.drop_detected = False
        self.silence_detected = False
        self.silence_since = 0

    def __call__(self, data):
        if self.silent_detector.detect(data):
            if not self.silence_detected:
                self.silence_detected = True
                self.silence_since = time_ns()
            if time_ns() - self.silence_since > 1.5 * 1e9:
                self.kick_detector.clear()
                self.break_detector.clear()
                self.drop_detector.clear()
                self.kick_visualizer.clear()
                self.break_detected = False
                self.drop_detected = False
                self.mh.on(PacketData(PacketType.NEW_MUSIC, PacketStatus.ON))
            # print("Silent detected, resetting kick and break detectors.")
            return True
        elif self.silence_detected:
            self.silence_detected = False
            self.mh.on(PacketData(PacketType.NEW_MUSIC, PacketStatus.OFF))
            print("Music started, resuming kick and break detection.")

        beat = self.kick_detector.detect(
            data, appendCurrentEnergy=not self.break_detected
        )

        if beat:
            if self.break_detected:
                self.break_detected = False
                self.break_detector.clear_old_beats()
                self.break_detector.clean_beats(
                    time_ns() - self.break_detector.beats[-1]
                )
                # print("Break detected.")
                self.mh.on(PacketData(PacketType.BREAK, PacketStatus.OFF))
            self.break_detector.on_beat()
            self.drop_detector.on_beat()
            print("beat detected")
            self.mh.on(PacketData(PacketType.BEAT, PacketStatus.ON))

        mbreak, drop = False, False
        if not self.break_detected and self.break_detector.detect(data):
            self.break_detected = True
            self.mh.on(PacketData(PacketType.BREAK, PacketStatus.ON))
            mbreak = True
        if not self.drop_detected and self.drop_detector.detect(data):
            self.drop_detected = True
            self.mh.on(PacketData(PacketType.DROP, PacketStatus.ON))
            drop = True
        if self.drop_detected and not self.drop_detector.detect(data):
            self.drop_detected = False
            self.mh.on(PacketData(PacketType.DROP, PacketStatus.OFF))
        self.kick_visualizer(
            data, beat_detected=beat, break_detected=mbreak, drop_detected=drop
        )
        self.mh.on(PacketData(PacketType.TICK, PacketStatus.ON))
        # self.snare_detector.detect(data)
        # self.snare_visualizer(data)
        # self.break_visualizer(data)
        return True


def update_plot(frame, listener):
    lines = []
    lines += [listener.kick_visualizer.line_energy, listener.kick_visualizer.line_limit]
    # Add all scatter markers (beat, break, drop)
    lines += [mt["scatter"] for mt in listener.kick_visualizer.marker_types.values()]
    # lines += listener.snare_visualizer.line_energy, listener.snare_visualizer.line_limit
    # lines += listener.break_visualizer.line_energy, listener.break_visualizer.line_limit
    return lines


def main():
    # Set up the audio stream.
    config = Config("config.json")

    if config.device_index == -2:
        pyaudio = PyAudio()
        for i in range(pyaudio.get_device_count()):
            device_info = pyaudio.get_device_info_by_index(i)
            print(f"Device {i}: {device_info['name']}")
        print("To auto select the default device, set device_index to -1.")
        config.device_index = int(
            input(
                f"Please select a device index from the list above [-1-{pyaudio.get_device_count() - 1}]:"
            )
        )
        if (
            config.device_index > pyaudio.get_device_count() - 1
            or config.device_index < -1
        ):
            print("Invalid device index. Exiting.")
            config.device_index = -2
            return
        else:
            config.save()

    audio_handler = AudioStreamHandler(SpectrumProcessor, config)
    print(f"Starting recording stream from device {audio_handler.device_index}")
    audio_handler.start_stream()

    # Set up the plot.
    fig, axs = plt.subplots(1, 1, figsize=(10, 8))
    listener = MainAudioListener(
        audio_handler.channels, audio_handler.chunk_size, audio_handler.sample_rate, axs
    )
    audio_handler.audio_capture.add_listener(listener)

    ani = animation.FuncAnimation(
        fig, update_plot, fargs=(listener,), interval=50, blit=True
    )
    plt.show()

    audio_handler.stop_stream()


if __name__ == "__main__":
    main()
