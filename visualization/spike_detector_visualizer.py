import os
import sys
import inspect
from collections import deque
from matplotlib.axes import Axes
# Fucking things to import from upper folder
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import audio.effects as effects

class SpikeDetectorVisualizer:
    def __init__(self, SpikeDetector: effects.SpikeDetector, ax: Axes, vizualisation_len=1000):
        self.SpikeDetector = SpikeDetector
        self.energy_history = deque(maxlen=vizualisation_len)
        self.limit_history = deque(maxlen=vizualisation_len)
        self.line_energy, = ax.plot([], [], lw=2, color='blue', label='Energy')
        self.line_limit, = ax.plot([], [], lw=2, color='red', label='Limit')
        self.ax = ax
        ax.set_xlim(0, vizualisation_len)
        #ax.set_ylim(0, 1e11)  # Initial ylim, adjust based on expected range
        ax.set_xlabel('Time')
        ax.set_ylabel('Energy')
        ax.set_title(type(SpikeDetector).__name__ + " Energy")
        ax.legend()

    def __call__(self, data):
        current_energy = data.get_ps_mean(self.SpikeDetector.freq_range)
        self.energy_history.append(current_energy)
        
        avg_energy = sum(self.SpikeDetector.energy_history) / len(self.SpikeDetector.energy_history)
        limit = self.SpikeDetector.sensitivity * avg_energy
        self.limit_history.append(limit)
        
        self.line_energy.set_ydata(self.energy_history)
        self.line_energy.set_xdata(range(len(self.energy_history)))
        self.line_limit.set_ydata(self.limit_history)
        self.line_limit.set_xdata(range(len(self.limit_history)))
        self.ax.relim()
        self.ax.autoscale_view()

        return self.line_energy, self.line_limit