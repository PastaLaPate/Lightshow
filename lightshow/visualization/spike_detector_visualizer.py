import importlib
import importlib.util
import traceback
from collections import deque
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Dict, List, Literal  # Import Empty for cleaner queue handling

import pyqtgraph as pg
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QVBoxLayout, QWidget

if importlib.util.find_spec("OpenGL", "GL"):
    OPENGL_AVAILABLE = True
    print("OpenGL available")
else:
    OPENGL_AVAILABLE = False
    print("OpenGL NOT available")


@dataclass
class Markers:
    x: List[int]
    y: List[int]
    dirty: bool


MarkerTypes = Literal["beat"] | Literal["break"] | Literal["drop"]


class SpikeDetectorVisualizer(QWidget):
    """Real-time spike visualizer using pyqtgraph for efficient plotting."""

    def __init__(
        self,
        spike_detector,
        visualization_len=1000,
        expected_max=2 * 1e13,
    ):
        super().__init__()
        self.spike_detector = spike_detector
        self.visualization_len = visualization_len
        self.expected_max = expected_max

        pg.setConfigOption("antialias", True)

        self.x_history = deque(maxlen=visualization_len)
        self.energy_history = deque(maxlen=visualization_len)
        self.diff_history = deque(maxlen=visualization_len)
        self.limit_history = deque(maxlen=visualization_len)
        self.global_index = 0

        self.marker_data: Dict[MarkerTypes, Markers] = {
            "beat": Markers(x=[], y=[], dirty=False),
            "break": Markers(x=[], y=[], dirty=False),
            "drop": Markers(x=[], y=[], dirty=False),
        }

        self.update_queue = Queue(maxsize=5)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._process_queued_updates)
        self.update_timer.start(int(1000 / 30))  # ~30 FPS

        # --- OPTIMIZATION 2: Enable OpenGL ---
        # useOpenGL=True offloads rendering to GPU.
        # Requires: pip install PyOpenGL
        self.plot = pg.PlotWidget(title="Spike Detector", useOpenGL=OPENGL_AVAILABLE)

        self.plot.setBackground("#1e1e1e")
        # Ensure antialiasing is off on the plot item specifically
        self.plot.setAntialiasing(False)
        plot_item = self.plot.getPlotItem()
        if plot_item:
            plot_item.setClipToView(True)
            plot_item.setDownsampling(mode="peak")

        self.plot.showGrid(x=False, y=False)
        self.plot.addLegend(offset=(10, 10))

        # (Pens setup remains the same...)
        pen_energy = pg.mkPen(color=(0, 255, 255), width=2)
        pen_diff = pg.mkPen(color=(255, 255, 0), width=1)
        pen_limit = pg.mkPen(
            color=(255, 0, 0), width=2, style=pg.QtCore.Qt.PenStyle.DashLine
        )

        self.energy_curve = self.plot.plot([], [], pen=pen_energy, name="Energy")
        self.diff_curve = self.plot.plot([], [], pen=pen_diff, name="Diff")
        self.limit_curve = self.plot.plot([], [], pen=pen_limit, name="Limit")

        # Optimization: Skip recording data for drawing if not needed
        self.energy_curve.setSkipFiniteCheck(True)
        self.diff_curve.setSkipFiniteCheck(True)

        self.energy_curve.setZValue(30)
        self.diff_curve.setZValue(20)
        self.limit_curve.setZValue(10)

        self.marker_items: Dict[MarkerTypes, pg.ScatterPlotItem] = {
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
            # Optimization: Scatter plots are heavy.
            # pxMode=True means size is in pixels, not data coordinates (faster)
            item.setPxMode(True)
            self.plot.addItem(item)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def __call__(
        self, data, beat_detected=False, break_detected=False, drop_detected=False
    ):
        try:
            self.update_queue.put_nowait(
                (data, beat_detected, break_detected, drop_detected)
            )
        except Exception:
            pass

    def _process_queued_updates(self):
        """Process ALL pending updates, then repaint ONCE."""
        updates_processed = 0
        max_per_frame = 10
        has_new_data = False

        try:
            while not self.update_queue.empty() and updates_processed < max_per_frame:
                try:
                    data_tuple = self.update_queue.get_nowait()
                    self._on_update_data(*data_tuple)
                    updates_processed += 1
                    has_new_data = True
                except Empty:
                    break
                except Exception:
                    traceback.print_exc()
            if has_new_data:
                self.qt_update()

        except Exception:
            traceback.print_exc()

    def _on_update_data(self, data, beat_detected, break_detected, drop_detected):
        try:
            current_energy = data.get_freq_mean([0, 40])

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
            self._add_marker("beat", beat_detected, current_energy)
            self._add_marker("break", break_detected, current_energy)
            self._add_marker("drop", drop_detected, current_energy)

            self.global_index += 1
        except Exception:
            traceback.print_exc()

    def _add_marker(self, marker_type, detected, current_energy):
        if detected:
            self.marker_data[marker_type].x.append(self.global_index)
            self.marker_data[marker_type].y.append(current_energy)
            # cap marker history
            maxlen = 200
            if len(self.marker_data[marker_type].x) > maxlen:
                self.marker_data[marker_type].x = self.marker_data[marker_type].x[
                    -maxlen:
                ]
                self.marker_data[marker_type].y = self.marker_data[marker_type].x[
                    -maxlen:
                ]
            self.marker_data[marker_type].dirty = True

    def qt_update(self):
        """Update plot items with buffered data."""
        if not self.x_history:
            return

        xs = list(self.x_history)
        energies = list(self.energy_history)
        diffs = list(self.diff_history)
        limits = list(self.limit_history)

        self.energy_curve.setData(xs, energies)
        self.diff_curve.setData(xs, diffs)

        if len(limits) > 0:
            lx = xs[-len(limits) :]
            self.limit_curve.setData(lx, list(limits))
        else:
            self.limit_curve.setData([], [])

        for mtype, item in self.marker_items.items():
            if self.marker_data[mtype].dirty:
                mx = self.marker_data[mtype].x
                my = self.marker_data[mtype].y
                item.setData(mx, my)

        max_x = self.global_index
        min_x = max(0, max_x - self.visualization_len)
        # Fixes pylance problems
        plot_item = self.plot.getPlotItem()
        if isinstance(plot_item, pg.PlotItem) and isinstance(plot_item.vb, pg.ViewBox):
            plot_item.vb.setXRange(min_x, max_x, padding=0)

    # (Clear method remains the same)
    def clear(self):
        self.update_timer.stop()
        self.x_history.clear()
        self.energy_history.clear()
        self.diff_history.clear()
        self.limit_history.clear()
        for marker_type in self.marker_data:
            self.marker_data[marker_type].x.clear()
            self.marker_data[marker_type].y.clear()
        self.energy_curve.setData([], [])
        self.diff_curve.setData([], [])
        self.limit_curve.setData([], [])
        for item in self.marker_items.values():
            item.setData([], [])
        while not self.update_queue.empty():
            self.update_queue.get_nowait()
        self.update_timer.start()
