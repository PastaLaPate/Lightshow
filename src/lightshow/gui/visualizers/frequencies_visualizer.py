import traceback

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from lightshow.audio.types import AudioData
from lightshow.core.logger import Logger
from lightshow.gui.utils import ui_signals

_logger = Logger.for_class("Audio Visualization")

_MAJOR_HZ = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
_MINOR_HZ = [
    30, 40, 60, 70, 80, 90,
    150, 300, 400, 700, 800, 900,
    1500, 3000, 4000, 6000, 7000, 8000, 15000,
]  # fmt: skip


def _hz_label(hz: int) -> str:
    return f"{hz // 1000}k" if hz >= 1000 else str(hz)


class FrequenciesVisualizer(QWidget):
    DB_FLOOR = -60.0

    def __init__(
        self,
        sample_rate: int = 44100,
        f_min: float = 20.0,
        f_max: float | None = None,
        n_points: int = 256,
        smooth_width: int = 5,
        attack: float = 0.6,
        release: float = 0.15,
        peak_decay_db: float = 0.05,
        fps: int = 120,
    ):
        super().__init__()
        nyquist = sample_rate / 2
        self.sample_rate = sample_rate
        self.f_min = float(f_min)
        self.f_max = float(min(f_max or nyquist, nyquist))
        self.n_points = n_points
        self._attack = attack
        self._release = release
        self._peak_decay_db = peak_decay_db

        if smooth_width > 1:
            k = np.hanning(smooth_width + 2)[1:-1]
            self._kernel = k / k.sum()
        else:
            self._kernel = np.ones(1)

        # State
        self._latest: np.ndarray | None = None  # written by audio thread
        self._n_bins = -1
        self._ref_db: float | None = None
        self._shown: np.ndarray | None = None
        self._error_shown = False

        self._setup_ui()
        self._setup_log_x_axis()

        self._timer = QTimer(self)
        self._timer.setInterval(max(1, 1000 // fps))
        self._timer.timeout.connect(self._render)
        self._timer.start()

    def _setup_ui(self) -> None:
        pg.setConfigOption("antialias", True)
        self.plot = pg.PlotWidget()
        self.plot.setBackground("#1e1e1e")

        plot_item = self.plot.getPlotItem()
        if plot_item is not None:
            plot_item.setLabel("bottom", "Frequency (Hz)")
            plot_item.setLabel("left", "Power (dB)")
            plot_item.getAxis("bottom").enableAutoSIPrefix(False)
            plot_item.getAxis("left").enableAutoSIPrefix(False)
            plot_item.getViewBox().setMouseEnabled(False, False)

        self.plot.showGrid(x=True, y=True, alpha=0.2)

        self.energy_curve = self.plot.plot(
            [],
            [],
            pen=pg.mkPen(color=(100, 255, 0), width=2),
            fillLevel=self.DB_FLOOR,
            brush=(100, 255, 0, 35),
        )
        self.energy_curve.setSkipFiniteCheck(True)
        self.energy_curve.setZValue(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def _setup_log_x_axis(self) -> None:
        plot_item = self.plot.getPlotItem()
        if plot_item is None:
            return

        in_range = lambda hz: self.f_min <= hz <= self.f_max
        major = [(np.log10(hz), _hz_label(hz)) for hz in _MAJOR_HZ if in_range(hz)]
        minor = [(np.log10(hz), "") for hz in _MINOR_HZ if in_range(hz)]
        plot_item.getAxis("bottom").setTicks([major, minor])

        self.plot.setXRange(np.log10(self.f_min), np.log10(self.f_max), padding=0)  # type: ignore
        self.plot.setYRange(self.DB_FLOOR, 0, padding=0.05)  # type: ignore

    def _build_grid(self, n_bins: int) -> None:
        fft_size = 2 * (n_bins - 1)
        self._bin_hz = np.fft.rfftfreq(fft_size, d=1.0 / self.sample_rate)

        edges = np.geomspace(self.f_min, self.f_max, self.n_points + 1)
        self._centers_hz = np.sqrt(edges[:-1] * edges[1:])
        self._x = np.log10(self._centers_hz)

        idx = np.clip(np.searchsorted(self._bin_hz, edges), 0, n_bins)
        starts, stops = idx[:-1], idx[1:]

        # Bands holding >= 2 bins use max-pooling; the others use interpolation.
        self._wide = (stops - starts) >= 2
        self._limit = max(int(stops[-1]), 1)
        # reduceat needs indices strictly inside the sliced array
        self._starts = np.minimum(starts, self._limit - 1)

        self._n_bins = n_bins
        self._shown = None  # shape changed, restart temporal smoothing

    def __call__(self, data: AudioData) -> None:
        self._latest = np.array(data.frequencies, dtype=np.float32, copy=True)

    def _render(self) -> None:
        power = self._latest
        if power is None:
            return
        self._latest = None

        try:
            if power.size < 2:
                return
            if power.size != self._n_bins:
                self._build_grid(power.size)

            # 1-2. dB per bin, then resample to the log grid
            db = 10.0 * np.log10(np.maximum(power, 1e-12))
            curve = np.interp(self._centers_hz, self._bin_hz, db)
            if self._wide.any():
                band_max = np.maximum.reduceat(db[: self._limit], self._starts)
                curve = np.where(self._wide, np.maximum(curve, band_max), curve)

            # 3. normalise against a smoothed running peak (never below 0 dB)
            peak = float(curve.max())
            if self._ref_db is None:
                self._ref_db = peak
            elif peak > self._ref_db:
                self._ref_db += 0.5 * (peak - self._ref_db)
            else:
                self._ref_db = max(self._ref_db - self._peak_decay_db, peak)
            ref = max(self._ref_db, 0.0)
            rel = np.clip(curve - ref, self.DB_FLOOR, 0.0)

            # 4. smooth along frequency
            if len(self._kernel) > 1:
                pad = len(self._kernel) // 2
                rel = np.convolve(
                    np.pad(rel, pad, mode="edge"), self._kernel, mode="valid"
                )

            # 5. attack / release over time
            if self._shown is None:
                self._shown = rel
            else:
                coef = np.where(rel > self._shown, self._attack, self._release)
                self._shown = self._shown + coef * (rel - self._shown)

            self.energy_curve.setData(self._x, self._shown)
        except Exception:  # noqa
            if not self._error_shown:  # don't spam a dialog at 60 Hz
                self._error_shown = True
                ui_signals.show_error.emit(
                    "UI Error",
                    f"Error when updating frequencies visualizer: \n {traceback.format_exc()}",
                )
