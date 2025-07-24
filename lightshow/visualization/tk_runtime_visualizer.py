import os
import sys
import inspect
# Fucking things to import from upper folder
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

from collections import deque
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from audio.effects.kick_detector import KickDetector
from audio.audio_streams import AudioData
from audio.processors import Processor

class RealTimeVisualizer:
    """
    Sets up a 2x2 grid of subplots and updates them in real time:
      - Top Left: Bar graph for raw FFT power spectrum.
      - Top Right: Time series for the average of the first 3 raw FFT bins.
      - Bottom Left: Bar graph for the Mel filter bank energies.
      - Bottom Right: Time series for the average of the first 3 Mel bands.
    Additionally, a kick detector flags kick beats when spikes occur in the low frequency energy.
    """
    def __init__(self, processor:Processor, sample_rate, chunk_size, duration=60, n_mels=40):
        self.processor = processor
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.n_mels = n_mels
        self.duration = duration
        self.start_time = time.time()
        self.chunks_per_second = sample_rate / chunk_size
        max_history = int(duration * self.chunks_per_second)
        self.raw_time_history = deque(maxlen=max_history)
        self.raw_avg_history = deque(maxlen=max_history)
        self.mel_time_history = deque(maxlen=max_history)
        self.mel_avg_history = deque(maxlen=max_history)
        self._setup_plots()
        # Initialize KickDetector with a 1-second window.
        self.kick_detector = KickDetector(int(self.chunks_per_second))
    
    def _setup_plots(self):
        self.fig, self.axs = plt.subplots(2, 2, figsize=(12, 8))
        # Top Left: Raw FFT Bar Graph.
        self.ax_raw_bar = self.axs[0, 0]
        self.bars_raw = self.ax_raw_bar.bar(
            self.processor.raw_freqs,
            np.zeros_like(self.processor.raw_freqs),
            width=(self.processor.raw_freqs[1] - self.processor.raw_freqs[0]),
            color='lightgreen'
        )
        self.ax_raw_bar.set_title("Raw FFT Power Spectrum")
        self.ax_raw_bar.set_xlabel("Frequency (Hz)")
        self.ax_raw_bar.set_ylabel("Power")
        self.ax_raw_bar.set_xlim([0, self.sample_rate / 2])
        self.ax_raw_bar.set_ylim([0, 1e10])
        # Top Right: Raw Time Series.
        self.ax_raw_time = self.axs[0, 1]
        self.line_raw, = self.ax_raw_time.plot([], [], lw=2, color='darkgreen')
        self.ax_raw_time.set_title("Average of First 3 Raw FFT Bins")
        self.ax_raw_time.set_xlabel("Time (s)")
        self.ax_raw_time.set_ylabel("Average Power")
        self.ax_raw_time.set_xlim(0, self.duration)
        self.ax_raw_time.set_ylim(0, 1e12)
        # Add a text annotation for kick detection.
        self.kick_annotation = self.ax_raw_time.text(
            0.05, 0.9, '', transform=self.ax_raw_time.transAxes,
            color='red', fontsize=14
        )
        # Bottom Left: Mel Filter Bank Bar Graph.
        self.ax_mel_bar = self.axs[1, 0]
        self.mel_indices = np.arange(self.n_mels)
        self.bars_mel = self.ax_mel_bar.bar(
            self.mel_indices,
            np.zeros(self.n_mels),
            color='skyblue'
        )
        self.ax_mel_bar.set_title("Mel Filter Bank")
        self.ax_mel_bar.set_xlabel("Mel Band Index")
        self.ax_mel_bar.set_ylabel("Energy")
        self.ax_mel_bar.set_xlim([-0.5, self.n_mels - 0.5])
        self.ax_mel_bar.set_ylim([0, 1e10])
        # Bottom Right: Mel Time Series.
        self.ax_mel_time = self.axs[1, 1]
        self.line_mel, = self.ax_mel_time.plot([], [], lw=2, color='darkblue')
        self.ax_mel_time.set_title("Average of First 3 Mel Bands")
        self.ax_mel_time.set_xlabel("Time (s)")
        self.ax_mel_time.set_ylabel("Average Energy")
        self.ax_mel_time.set_xlim(0, self.duration)
        self.ax_mel_time.set_ylim([0, 1e10])

    def update(self, frame, audio_capture):
        data = audio_capture.get_latest_data()
        if data is not None:
            # Process the latest audio chunk.
            audio_data= self.processor.process(data)
            power_spectrum, mel_energies = audio_data.power_spectrum, audio_data.mel_energies
            raw_avg = audio_data.get_ps_mean([0, 3])
            mel_avg = audio_data.get_ps_mean([0, 3])
            # Update raw FFT bars.
            for rect, pwr in zip(self.bars_raw, power_spectrum):
                rect.set_height(pwr)
            # Update Mel filter bank bars.
            for rect, energy in zip(self.bars_mel, mel_energies):
                rect.set_height(energy)
            current_time = time.time() - self.start_time
            self.raw_time_history.append(current_time)
            self.raw_avg_history.append(raw_avg)
            self.mel_time_history.append(current_time)
            self.mel_avg_history.append(mel_avg)
            # Update raw time series line.
            self.line_raw.set_data(
                np.array(self.raw_time_history),
                np.array(self.raw_avg_history)
            )
            # Update Mel time series line.
            self.line_mel.set_data(
                np.array(self.mel_time_history),
                np.array(self.mel_avg_history)
            )
            # Adjust x-axis limits to show the last 'duration' seconds.
            if current_time > self.duration:
                self.ax_raw_time.set_xlim(current_time - self.duration, current_time)
                self.ax_mel_time.set_xlim(current_time - self.duration, current_time)
            # Kick detection: if a kick is detected, update the annotation.
            if self.kick_detector.detect(audio_data):
                self.kick_annotation.set_text("Kick detected!")
            else:
                self.kick_annotation.set_text("")
        return [*self.bars_raw, self.line_raw, *self.bars_mel, self.line_mel, self.kick_annotation]

    def start(self, audio_capture):
        self.ani = animation.FuncAnimation(
            self.fig,
            self.update,
            fargs=(audio_capture,),
            interval=1,
            blit=True
        )
        plt.tight_layout()
        plt.show()