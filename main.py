"""
Real-time audio spectrum visualization with kick detection.
"""
from collections import deque
import traceback
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation

import pyaudiowpatch as pyaudio
from _spinner_helper import Spinner
from audio.processors import SpectrumProcessor
from audio.effects.kick_detector import KickDetector
from audio.audio_streams import AudioCapture, AudioStreamHandler, AudioListener

class MainAudioListener(AudioListener):
    def __init__(self, channels, chunk_size, sample_rate):
        super().__init__(channels, chunk_size, sample_rate)
        self.kick_detector = KickDetector(int(sample_rate / chunk_size))
        self.kick_count = 0
        self.detecting_kick = False
        self.energy_history = deque(maxlen=1000)  # Store energy values for plotting
        self.limit_history = deque(maxlen=1000)  # Store limit values for plotting
        self.detected_history = deque(maxlen=1000)  # Store detected values for plotting

    def process(self, data):
        current_energy = data.get_ps_mean(self.kick_detector.freq_range)
        self.energy_history.append(current_energy)

        avg_energy = sum(self.energy_history) / len(self.energy_history)
        limit = self.kick_detector.sensitivity * avg_energy
        self.limit_history.append(limit)

        if self.kick_detector.detect(data):
            if not self.detecting_kick:
                self.detecting_kick = True
                self.kick_count += 1
                print(f"Kick detected! Total kicks: {self.kick_count}")
        else:
            self.detecting_kick = False

        self.detected_history.append(3 * 1e12 if self.detecting_kick else 3 * 1e10)
        return True

def update_plot(frame, listener, line_energy, line_limit, line_detected):
    line_energy.set_ydata(listener.energy_history)
    line_energy.set_xdata(range(len(listener.energy_history)))
    line_limit.set_ydata(listener.limit_history)
    line_limit.set_xdata(range(len(listener.limit_history)))
    line_detected.set_ydata(listener.detected_history)
    line_detected.set_xdata(range(len(listener.detected_history)))
    return line_energy, line_limit, line_detected

def main():
    with Spinner() as spinner:
        try:
            # Set up the audio stream.
            audio_handler = AudioStreamHandler(SpectrumProcessor, chunk_size=512)
            spinner.print(f"Recording from device index: {audio_handler.device_index}")
            audio_handler.start_stream()
            listener = MainAudioListener(audio_handler.channels, audio_handler.chunk_size, audio_handler.sample_rate)
            audio_handler.audio_capture.add_listener(lambda *args: listener)
            spinner.stop()

            # Set up the plot.
            fig, ax = plt.subplots()
            line_energy, = ax.plot([], [], lw=2, label='Energy')
            line_limit, = ax.plot([], [], lw=2, label='Limit', color='red')
            line_detecting, = ax.plot([], [], lw=2, label='Detected', color='green')
            ax.set_ylim(0, 1e13)  # Adjust based on expected energy range
            ax.set_xlim(0, 1000)  # Adjust based on the length of energy history
            ax.set_title("Kick Detector Energy")
            ax.set_xlabel("Time")
            ax.set_ylabel("Energy")
            ax.legend()

            ani = animation.FuncAnimation(fig, update_plot, fargs=(listener, line_energy, line_limit, line_detecting), interval=50, blit=True)
            plt.show()

        except Exception as e:
            spinner.print(traceback.format_exc())
        finally:
            audio_handler.stop_stream()

if __name__ == "__main__":
    main()
