"""
Real-time audio spectrum visualization with kick detection.
"""
from collections import deque
import matplotlib.pyplot as plt
import matplotlib.animation as animation

import numpy as np
from audio.processors import SpectrumProcessor
from audio.effects.kick_detector import KickDetector
from audio.effects.spike_detector import SpikeDetector, DetectionType
from audio.audio_streams import AudioStreamHandler, AudioListener

class MainAudioListener(AudioListener):
    def __init__(self, channels, chunk_size, sample_rate):
        super().__init__(channels, chunk_size, sample_rate)
        self.kick_detector = KickDetector(int(sample_rate / chunk_size))
        self.kick_count = 0
        self.detecting_kick = False
        self.energy_history = deque(maxlen=1000)  # Store energy values for plotting
        self.limit_history = deque(maxlen=1000)  # Store limit values for plotting
        self.detected_history = deque(maxlen=1000)  # Store detected values for plotting
        # Global Energy
        self.global_detector = SpikeDetector(int(sample_rate / chunk_size), 7.5, 100, [20, 20_000], DetectionType.UPPER)
        self.global_detector2 = SpikeDetector(int(sample_rate / chunk_size), 1, 1000, [20, 20_000], DetectionType.UPPER)
        self.global_energy_history = deque(maxlen=1000)  # Store energy values for plotting
        self.global_limit_history = deque(maxlen=1000)  # Store limit values for plotting
        self.global_limit2_history = deque(maxlen=1000)  # Store limit values for plotting

    def __call__(self, data):
        current_energy = data.get_ps_mean(self.kick_detector.freq_range)
        self.energy_history.append(current_energy)
        print(data.get_ps_mean([0, 20000]))
        avg_energy = np.mean(self.kick_detector.energy_history)
        limit = self.kick_detector.sensitivity * avg_energy
        self.limit_history.append(limit)

        if self.kick_detector.detect(data):
            if not self.detecting_kick:
                self.detecting_kick = True
                self.kick_count += 1
                print(f"Kick detected! Total kicks: {self.kick_count}")
        else:
            self.detecting_kick = False
        self.detected_history.append(np.mean(self.energy_history))
        #self.detected_history.append(3 * 1e12 if self.detecting_kick else 3 * 1e10)

        current_energy = data.get_ps_mean(self.global_detector.freq_range)
        self.global_energy_history.append(current_energy)
        self.global_detector.energy_history.append(current_energy)
        self.global_detector2.energy_history.append(current_energy)
        self.global_limit_history.append(self.global_detector.sensitivity * np.mean(self.global_detector.energy_history))
        self.global_limit2_history.append(self.global_detector2.sensitivity * np.mean(self.global_detector2.energy_history))
        return True

def update_plot(frame, listener, line_energy, line_limit, line_detected, line_energy_global, line_energy_limit, line_energy_limit2):
    line_energy.set_ydata(listener.energy_history)
    line_energy.set_xdata(range(len(listener.energy_history)))
    line_limit.set_ydata(listener.limit_history)
    line_limit.set_xdata(range(len(listener.limit_history)))
    line_detected.set_ydata(listener.detected_history)
    line_detected.set_xdata(range(len(listener.detected_history)))

    line_energy_global.set_ydata(listener.global_energy_history)
    line_energy_global.set_xdata(range(len(listener.global_energy_history)))
    line_energy_limit.set_ydata(listener.global_limit_history)
    line_energy_limit.set_xdata(range(len(listener.global_limit_history)))
    line_energy_limit2.set_ydata(listener.global_limit2_history)
    line_energy_limit2.set_xdata(range(len(listener.global_limit2_history)))

    return line_energy, line_limit, line_detected, line_energy_global, line_energy_limit, line_energy_limit2

def main():
    #with Spinner() as spinner:
        # Set up the audio stream.
    audio_handler = AudioStreamHandler(SpectrumProcessor, chunk_size=512)
    print(f"Recording from device index: {audio_handler.device_index}")
    audio_handler.start_stream()
    listener = MainAudioListener(audio_handler.channels, audio_handler.chunk_size, audio_handler.sample_rate)
    audio_handler.audio_capture.add_listener(listener)

    # Set up the plot.
    fig, axs = plt.subplots(1, 2)
    ax = axs[0]
    line_energy, = ax.plot([], [], lw=2, label='Energy')
    line_limit, = ax.plot([], [], lw=2, label='Limit (10000?)', color='red')
    line_detecting, = ax.plot([], [], lw=2, label='Detected (1000)', color='green')
    ax.set_ylim(0, 1e11*2)  # Adjust based on expected energy range
    ax.set_xlim(0, 1000)  # Adjust based on the length of energy history
    ax.set_title("Kick Detector Energy")
    ax.set_xlabel("Time")
    ax.set_ylabel("Energy")
    ax.legend()
    ax = axs[1]
    line_energy_global, = ax.plot([], [], lw=2, label='Energy')
    line_energy_limit, = ax.plot([], [], lw=2, label='Limit (100)', color='red')
    line_energy_limit2, = ax.plot([], [], lw=2, label='Limit (1000)', color='green')
    ax.set_ylim(0, 1e9*2)  # Adjust based on expected energy range
    ax.set_xlim(0, 1000)  # Adjust based on the length of energy history
    ax.set_title("Global Energy")
    ax.set_xlabel("Time")
    ax.set_ylabel("Energy")
    ax.legend()

    ani = animation.FuncAnimation(fig, update_plot, fargs=(listener, line_energy, line_limit, line_detecting,
                                                            line_energy_global, line_energy_limit, line_energy_limit2), interval=50, blit=True)
    plt.show()

    audio_handler.stop_stream()

if __name__ == "__main__":
    main()
