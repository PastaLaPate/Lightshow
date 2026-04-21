import importlib.util
import traceback

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from lightshow.audio.audio_types import AudioData
from lightshow.gui.utils import ui_signals
from lightshow.utils.logger import Logger

_logger = Logger.for_class("Audio Visualization")

if importlib.util.find_spec("OpenGL", "GL"):
    OPENGL_AVAILABLE = True
    _logger.debug("Using OpenGL")
else:
    OPENGL_AVAILABLE = False
    _logger.warn("Unable to use OpenGL. Expect poor performance")


def _hermite_interpolate(values: np.ndarray, upsample: int = 8) -> np.ndarray:
    n = len(values)
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
    )
    return segments.T.ravel()


class FrequenciesVisualizer(QWidget):
    """
    Real-time spectrum visualizer with:
    - Log-scaled frequency axis (Hz labels)
    - Log-scaled power axis (dB)
    - Hermite-smoothed curve
    """

    SAMPLE_RATE = 44100
    CHUNK_SIZE = 1024

    def __init__(
        self,
        freq_range: tuple[int, int] = (0, 2049),
        sample_rate: int = SAMPLE_RATE,
        chunk_size: int = CHUNK_SIZE,
        upsample: int = 4,
    ):
        super().__init__()
        self.freq_range = freq_range
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.upsample = upsample

        # Hz value for each FFT bin

        self._peak_ref = 1.0  # running maximum, updated each frame
        self._bin_hz = np.fft.rfftfreq(
            chunk_size, d=1.0 / sample_rate
        )  # shape: (n_bins,)

        self._setup_ui()
        self._setup_log_x_axis()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        pg.setConfigOption("antialias", True)
        self.plot = pg.PlotWidget(useOpenGL=OPENGL_AVAILABLE)
        self.plot.setBackground("#1e1e1e")

        plot_item = self.plot.getPlotItem()
        if plot_item:
            plot_item.setClipToView(True)
            plot_item.setDownsampling(mode="peak")
            plot_item.setLabel("bottom", "Frequency", units="Hz")
            plot_item.setLabel("left", "Power", units="dB")

        self.plot.showGrid(x=True, y=True, alpha=0.2)

        pen = pg.mkPen(color=(100, 255, 0), width=2)
        self.energy_curve = self.plot.plot([], [], pen=pen)
        self.energy_curve.setSkipFiniteCheck(True)
        self.energy_curve.setZValue(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def _setup_log_x_axis(self) -> None:
        """Replace the bottom axis with a log-scaled one with Hz tick labels."""
        plot_item = self.plot.getPlotItem()
        if not plot_item:
            return

        # Work in log10(Hz) space on the x-axis
        # Place ticks at round Hz values
        major_hz = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
        minor_hz = [
            30,
            40,
            60,
            70,
            80,
            90,
            150,
            300,
            400,
            700,
            800,
            900,
            1500,
            3000,
            4000,
            6000,
            7000,
            8000,
            15000,
        ]

        def hz_label(hz: int) -> str:
            return f"{hz // 1000}k" if hz >= 1000 else str(hz)

        major_ticks = [(np.log10(hz), hz_label(hz)) for hz in major_hz]
        minor_ticks = [(np.log10(hz), "") for hz in minor_hz]

        axis = plot_item.getAxis("bottom")
        axis.setTicks([major_ticks, minor_ticks])

        # Set x range in log10 space: 20 Hz → nyquist
        nyquist = self.sample_rate / 2
        # ty getting wrong types for some reason, so ignore type checking here
        self.plot.setXRange(np.log10(20), np.log10(nyquist), padding=0)  # type: ignore
        self.plot.setYRange(-60, 0, padding=0.05)  # type: ignore

    # ------------------------------------------------------------------
    # Precompute log-spaced x positions for the visible bins
    # ------------------------------------------------------------------

    def _log_x_for_bins(self, bin_indices: np.ndarray) -> np.ndarray:
        # Clamp indices to valid range
        clamped = np.clip(bin_indices, 0, len(self._bin_hz) - 1)
        hz = self._bin_hz[clamped]
        hz = np.where(hz < 1.0, 1.0, hz)
        return np.log10(hz)

    # ------------------------------------------------------------------
    # Audio callback
    # ------------------------------------------------------------------

    def __call__(self, data: AudioData) -> None:
        try:
            lo, hi = self.freq_range
            hi = min(hi, len(data.frequencies))
            lo = max(lo, 0)
            bins = data.frequencies[lo:hi].astype(np.float32)
            if bins.size < 2:
                return

            # Update running peak with slow decay so it tracks loud moments
            frame_max = float(bins.max())
            if frame_max > self._peak_ref:
                self._peak_ref = frame_max
            else:
                self._peak_ref *= 0.995  # slow decay
            self._peak_ref = max(self._peak_ref, 1.0)  # never divide by zero

            # Convert to dB relative to running peak → range (-inf, 0]
            EPS = 1e-10
            db = 10.0 * np.log10(np.maximum(bins, EPS) / self._peak_ref)
            db = np.clip(db, -60.0, 0.0)

            # Hermite smooth
            smoothed = _hermite_interpolate(db, upsample=self.upsample)

            # Log x axis
            n = len(data.frequencies)
            if not hasattr(self, "_last_n") or self._last_n != n:
                self._bin_hz = np.fft.rfftfreq(2 * (n - 1), d=1.0 / self.sample_rate)
                self._last_n = n
                self._setup_log_x_axis()

            bin_indices = np.arange(lo, lo + len(bins))
            log_x = self._log_x_for_bins(bin_indices)
            x_up = np.interp(
                np.linspace(0, len(log_x) - 1, len(smoothed)),
                np.arange(len(log_x)),
                log_x,
            )

            self.energy_curve.setData(x_up, smoothed)
        except Exception:
            ui_signals.show_error.emit(
                "UI Error",
                f"Error when updating frequencies visualizer: \n {traceback.format_exc()}",
            )
