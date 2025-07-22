import os
import sys
import inspect
from collections import deque
from matplotlib.axes import Axes
import numpy as np
# Fucking things to import from upper folder
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import audio.effects as effects
class SpikeDetectorVisualizer:
    def __init__(self, SpikeDetector: effects.SpikeDetector, ax: Axes, vizualisation_len=1000, expectedMax=2*1e13):
        self.SpikeDetector = SpikeDetector
        self.energy_history = deque(maxlen=vizualisation_len)
        self.limit_history = deque(maxlen=vizualisation_len)
        self.beat_indices = []  # Store global indices of beats
        self.beat_energies = [] # Store energies at beat times
        self.global_index = 0   # Global sample index
        self.line_energy, = ax.plot([], [], lw=2, color='blue', label='Energy')
        self.line_limit, = ax.plot([], [], lw=2, color='red', label='Limit')
        self.scatter_beats = ax.scatter([], [], color='magenta', label='Beat', zorder=5)
        self.ax = ax
        ax.set_xlim(0, vizualisation_len)
        ax.set_ylim(0, expectedMax) 
        ax.set_xlabel('Time')
        ax.set_ylabel('Energy')
        ax.set_title(type(SpikeDetector).__name__ + " Energy")
        ax.legend()

    def __call__(self, data, beat_detected=False):
        current_energy = data.get_ps_mean(self.SpikeDetector.freq_range)
        self.energy_history.append(current_energy)
        avg_energy = sum(self.SpikeDetector.energy_history) / len(self.SpikeDetector.energy_history)
        limit = self.SpikeDetector.sensitivity * avg_energy
        self.limit_history.append(limit)

        self.line_energy.set_ydata(self.energy_history)
        self.line_energy.set_xdata(range(len(self.energy_history)))
        self.line_limit.set_ydata(self.limit_history)
        self.line_limit.set_xdata(range(len(self.limit_history)))

        # Add marker if beat detected
        if beat_detected:
            self.beat_indices.append(self.global_index)
            self.beat_energies.append(current_energy)
            # Optionally, keep only recent beats to avoid memory growth
            if len(self.beat_indices) > 10 * self.energy_history.maxlen:
                self.beat_indices = self.beat_indices[-10 * self.energy_history.maxlen:]
                self.beat_energies = self.beat_energies[-10 * self.energy_history.maxlen:]

        # Only show markers within the current window
        window_start = self.global_index - len(self.energy_history) + 1
        visible_beats = [
            (idx - window_start, energy)
            for idx, energy in zip(self.beat_indices, self.beat_energies)
            if window_start <= idx < self.global_index + 1
        ]
        if visible_beats:
            offsets = np.array(visible_beats)
        else:
            offsets = np.empty((0, 2))
        self.scatter_beats.set_offsets(offsets)

        self.global_index += 1  # Increment global index for each call

        return self.line_energy, self.line_limit, self.scatter_beats