"""
Real-time audio spectrum visualization with kick detection.
"""
from collections import deque
import matplotlib.pyplot as plt
import matplotlib.animation as animation

import numpy as np
from audio.processors import SpectrumProcessor
import audio.effects as effects
from audio.audio_streams import AudioStreamHandler, AudioListener
from visualization.spike_detector_visualizer import SpikeDetectorVisualizer

class MainAudioListener(AudioListener):
    def __init__(self, channels, chunk_size, sample_rate, ax_kick, ax_snare, ax_break):
        super().__init__(channels, chunk_size, sample_rate)
        self.kick_detector = effects.KickDetector(int(sample_rate / chunk_size))
        self.snare_detector = effects.SnareDetector(int(sample_rate / chunk_size))
        self.break_detector = effects.BreakDetector(int(sample_rate / chunk_size))
        
        self.kick_visualizer = SpikeDetectorVisualizer(self.kick_detector, ax_kick)
        self.snare_visualizer = SpikeDetectorVisualizer(self.snare_detector, ax_snare)
        self.break_visualizer = SpikeDetectorVisualizer(self.break_detector, ax_break)

    def __call__(self, data):
        self.kick_detector.detect(data)
        self.kick_visualizer(data)
        self.snare_detector.detect(data)
        self.snare_visualizer(data)
        self.break_detector.detect(data)
        self.break_visualizer(data)
        return True

def update_plot(frame, listener):
    return listener.kick_visualizer.line_energy, listener.kick_visualizer.line_limit, \
           listener.snare_visualizer.line_energy, listener.snare_visualizer.line_limit, \
           listener.break_visualizer.line_energy, listener.break_visualizer.line_limit

def main():
    # Set up the audio stream.
    audio_handler = AudioStreamHandler(SpectrumProcessor, chunk_size=512)
    print(f"Recording from device index: {audio_handler.device_index}")
    audio_handler.start_stream()

    # Set up the plot.
    fig, axs = plt.subplots(3, 1, figsize=(10, 8))
    listener = MainAudioListener(audio_handler.channels, audio_handler.chunk_size, audio_handler.sample_rate, axs[0], axs[1], axs[2])
    audio_handler.audio_capture.add_listener(listener)

    ani = animation.FuncAnimation(fig, update_plot, fargs=(listener,), interval=50, blit=True)
    plt.show()

    audio_handler.stop_stream()

if __name__ == "__main__":
    main()
