import importlib
import importlib.util
import traceback

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from lightshow.audio.audio_types import AudioData
from lightshow.utils.logger import Logger

_logger = Logger.for_class("Audio Visualization")

if importlib.util.find_spec("OpenGL", "GL"):
    OPENGL_AVAILABLE = True
    _logger.debug("Using OpenGL")
else:
    OPENGL_AVAILABLE = False
    _logger.warn("Unable to use OpenGL. Expect poor performance")


def _hermite_interpolate(values: np.ndarray, upsample: int = 8) -> np.ndarray:
    """
    Resample `values` using cubic Hermite (Catmull-Rom) splines.
    Returns an array of length (len(values) - 1) * upsample.
    """
    n = len(values)
    # Catmull-Rom tangents: m[i] = 0.5 * (v[i+1] - v[i-1])
    m = np.empty(n)
    m[0] = values[1] - values[0]
    m[-1] = values[-1] - values[-2]
    m[1:-1] = 0.5 * (values[2:] - values[:-2])

    t = np.linspace(0.0, 1.0, upsample, endpoint=False)
    t2, t3 = t**2, t**3

    h00 = 2 * t3 - 3 * t2 + 1
    h10 = t3 - 2 * t2 + t
    h01 = -2 * t3 + 3 * t2
    h11 = t3 - t2

    segments = (
        np.outer(h00, values[:-1])
        + np.outer(h10, m[:-1])
        + np.outer(h01, values[1:])
        + np.outer(h11, m[1:])
    )  # shape: (upsample, n-1)

    return np.maximum(0.0, segments.T.ravel())  # flatten: (n-1)*upsample


class FrequenciesVisualizer(QWidget):
    """Real-time frequencies visualizer using pyqtgraph and cubic Hermite splines."""

    def __init__(self, freq_ranges=(0, 2049)):
        super().__init__()
        self.freq_ranges = freq_ranges

        pg.setConfigOption("antialias", True)
        self.plot = pg.PlotWidget(title="Spectrum", useOpenGL=OPENGL_AVAILABLE)
        self.plot.setBackground("#1e1e1e")
        self.plot.setAntialiasing(False)

        plot_item = self.plot.getPlotItem()
        if plot_item:
            plot_item.setClipToView(True)
            plot_item.setDownsampling(mode="peak")

        self.plot.showGrid(x=False, y=False)
        self.plot.addLegend(offset=(10, 10))

        pen = pg.mkPen(color=(100, 255, 0), width=2)
        self.energy_curve = self.plot.plot([], [], pen=pen, name="Freq")
        self.energy_curve.setSkipFiniteCheck(True)
        self.energy_curve.setZValue(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def __call__(self, data: AudioData) -> None:
        try:
            bins = data.frequencies[self.freq_ranges[0] : self.freq_ranges[1]]
            self.energy_curve.setData(bins)
        except Exception:
            traceback.print_exc()
