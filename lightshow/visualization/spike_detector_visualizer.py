from collections import deque

import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from lightshow.audio import detectors


class SpikeDetectorVisualizer(QWidget):
    """Real-time spike visualizer using pyqtgraph for efficient plotting."""

    def __init__(
        self,
        spike_detector: detectors.SpikeDetector,
        visualization_len=1000,
        expected_max=2 * 1e13,
    ):
        super().__init__()
        self.spike_detector = spike_detector
        self.visualization_len = visualization_len
        self.expected_max = expected_max

        # Data buffers (store x indices and values)
        self.x_history = deque(maxlen=visualization_len)
        self.energy_history = deque(maxlen=visualization_len)
        self.diff_history = deque(maxlen=visualization_len)
        self.limit_history = deque(maxlen=visualization_len)
        self.global_index = 0

        # Marker storage
        self.marker_data = {
            "beat": {"x": [], "y": []},
            "break": {"x": [], "y": []},
            "drop": {"x": [], "y": []},
        }

        pg.setConfigOption("useOpenGL", True)
        pg.setConfigOption("antialias", True)

        # Setup pyqtgraph plot
        self.plot = pg.PlotWidget(title="Spike Detector")
        self.plot.setBackground("#1e1e1e")
        self.plot.setAntialiasing(True)
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.addLegend(offset=(10, 10))

        pen_energy = pg.mkPen(color=(0, 255, 255), width=2)
        pen_diff = pg.mkPen(color=(255, 255, 0), width=1)
        pen_limit = pg.mkPen(
            color=(255, 0, 0), width=2, style=pg.QtCore.Qt.PenStyle.DashLine
        )

        self.energy_curve = self.plot.plot([], [], pen=pen_energy, name="Energy")
        self.diff_curve = self.plot.plot([], [], pen=pen_diff, name="Diff")
        self.limit_curve = self.plot.plot([], [], pen=pen_limit, name="Limit")
        self.energy_curve.setZValue(30)
        self.diff_curve.setZValue(20)
        self.limit_curve.setZValue(10)

        # Scatter items for markers
        self.marker_items = {
            "beat": pg.ScatterPlotItem(
                [], [], pen=pg.mkPen(None), brush=pg.mkBrush(0, 255, 0), size=6
            ),
            "break": pg.ScatterPlotItem(
                [], [], pen=pg.mkPen(None), brush=pg.mkBrush(255, 165, 0), size=6
            ),
            "drop": pg.ScatterPlotItem(
                [], [], pen=pg.mkPen(None), brush=pg.mkBrush(255, 0, 255), size=6
            ),
        }
        for name, item in self.marker_items.items():
            item.setZValue(40)
            self.plot.addItem(item)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def __call__(
        self, data, beat_detected=False, break_detected=False, drop_detected=False
    ):
        """Append new sample data and record markers.

        The actual plotting is done in `qt_update` to avoid heavy work in the audio thread.
        """
        current_energy = data.get_ps_mean(self.spike_detector.freq_range)

        self.x_history.append(self.global_index)
        self.energy_history.append(current_energy)

        if len(self.energy_history) > 3:
            diff = (
                self.energy_history[-1] - self.energy_history[-4]
                if self.energy_history[-1] > self.energy_history[-4]
                else 0
            )
        else:
            diff = 0
        self.diff_history.append(diff)

        if len(self.spike_detector.energy_history) < 1:
            self.global_index += 1
            return

        avg_energy = sum(self.spike_detector.energy_history) / len(
            self.spike_detector.energy_history
        )
        limit = self.spike_detector.sensitivity * avg_energy
        self.limit_history.append(limit)

        # Add markers
        self._add_marker("beat", beat_detected, current_energy)
        self._add_marker("break", break_detected, current_energy)
        self._add_marker("drop", drop_detected, current_energy)

        self.global_index += 1

    def _add_marker(self, marker_type, detected, current_energy):
        if detected:
            self.marker_data[marker_type]["x"].append(self.global_index)
            self.marker_data[marker_type]["y"].append(current_energy)
            # cap marker history
            maxlen = 200
            if len(self.marker_data[marker_type]["x"]) > maxlen:
                self.marker_data[marker_type]["x"] = self.marker_data[marker_type]["x"][
                    -maxlen:
                ]
                self.marker_data[marker_type]["y"] = self.marker_data[marker_type]["y"][
                    -maxlen:
                ]

    def qt_update(self):
        """Update plot items with buffered data. Called from the GUI timer."""
        if not self.x_history:
            return

        xs = list(self.x_history)
        energies = list(self.energy_history)
        diffs = list(self.diff_history)
        limits = list(self.limit_history)

        # Update curves
        self.energy_curve.setData(xs, energies)
        self.diff_curve.setData(xs, diffs)
        # limit may be shorter than xs; align by using last N values
        if len(limits) > 0:
            lx = xs[-len(limits) :]
            self.limit_curve.setData(lx, list(limits))
        else:
            self.limit_curve.setData([], [])

        # Update marker scatter plots
        for mtype, item in self.marker_items.items():
            mx = self.marker_data[mtype]["x"]
            my = self.marker_data[mtype]["y"]
            item.setData(mx, my)

        # Keep view to latest window
        max_x = self.global_index
        min_x = max(0, max_x - self.visualization_len)
        self.plot.setXRange(min_x, max_x)

    def clear(self):
        self.x_history.clear()
        self.energy_history.clear()
        self.diff_history.clear()
        self.limit_history.clear()
        for marker_type in self.marker_data:
            self.marker_data[marker_type]["x"].clear()
            self.marker_data[marker_type]["y"].clear()
        # Clear plot items
        self.energy_curve.setData([], [])
        self.diff_curve.setData([], [])
        self.limit_curve.setData([], [])
        for item in self.marker_items.values():
            item.setData([], [])
