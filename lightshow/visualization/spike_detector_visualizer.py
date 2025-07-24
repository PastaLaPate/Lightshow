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
        self.global_index = 0   # Global sample index

        # Marker data
        self.marker_types = {
            'beat': {'indices': [], 'energies': [], 'scatter': ax.scatter([], [], color='magenta', label='Beat', zorder=5)},
            'break': {'indices': [], 'energies': [], 'scatter': ax.scatter([], [], color='green', label='Break', zorder=5)},
            'drop': {'indices': [], 'energies': [], 'scatter': ax.scatter([], [], color='orange', label='Drop', zorder=5)},
        }

        self.line_energy, = ax.plot([], [], lw=2, color='blue', label='Energy')
        self.line_limit, = ax.plot([], [], lw=2, color='red', label='Limit')
        self.ax = ax
        ax.set_xlim(0, vizualisation_len)
        ax.set_ylim(0, expectedMax) 
        ax.set_xlabel('Time')
        ax.set_ylabel('Energy')
        ax.set_title(type(SpikeDetector).__name__ + " Energy")
        ax.legend()

    def _add_marker(self, marker_type, detected, current_energy):
        if detected:
            self.marker_types[marker_type]['indices'].append(self.global_index)
            self.marker_types[marker_type]['energies'].append(current_energy)
            # Limit memory growth
            maxlen = 10 * self.energy_history.maxlen
            if len(self.marker_types[marker_type]['indices']) > maxlen:
                self.marker_types[marker_type]['indices'] = self.marker_types[marker_type]['indices'][-maxlen:]
                self.marker_types[marker_type]['energies'] = self.marker_types[marker_type]['energies'][-maxlen:]

    def _update_scatter(self, marker_type):
        indices = self.marker_types[marker_type]['indices']
        energies = self.marker_types[marker_type]['energies']
        window_start = self.global_index - len(self.energy_history) + 1
        visible = [
            (idx - window_start, energy)
            for idx, energy in zip(indices, energies)
            if window_start <= idx < self.global_index + 1
        ]
        offsets = np.array(visible) if visible else np.empty((0, 2))
        self.marker_types[marker_type]['scatter'].set_offsets(offsets)

    def __call__(self, data, beat_detected=False, break_detected=False, drop_detected=False):
        current_energy = data.get_ps_mean(self.SpikeDetector.freq_range)
        self.energy_history.append(current_energy)
        if len(self.SpikeDetector.energy_history) < 1:
            return self.line_energy, self.line_limit, *(mt['scatter'] for mt in self.marker_types.values())
        avg_energy = sum(self.SpikeDetector.energy_history) / len(self.SpikeDetector.energy_history)
        limit = self.SpikeDetector.sensitivity * avg_energy
        self.limit_history.append(limit)

        self.line_energy.set_ydata(self.energy_history)
        self.line_energy.set_xdata(range(len(self.energy_history)))
        self.line_limit.set_ydata(self.limit_history)
        self.line_limit.set_xdata(range(len(self.limit_history)))

        # Add markers
        self._add_marker('beat', beat_detected, current_energy)
        self._add_marker('break', break_detected, current_energy)
        self._add_marker('drop', drop_detected, current_energy)

        # Update scatter plots
        for marker_type in self.marker_types:
            self._update_scatter(marker_type)

        self.global_index += 1  # Increment global index for each call

        return self.line_energy, self.line_limit, *(mt['scatter'] for mt in self.marker_types.values())

    def clear(self):
        self.energy_history.clear()
        self.limit_history.clear()
        self.global_index = 0
        empty = np.empty((0,))
        self.line_energy.set_xdata(empty)
        self.line_energy.set_ydata(empty)
        self.line_limit.set_xdata(empty)
        self.line_limit.set_ydata(empty)
        for mt in self.marker_types.values():
            mt['indices'].clear()
            mt['energies'].clear()
            mt['scatter'].set_offsets(np.empty((0, 2)))