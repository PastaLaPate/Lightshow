import numpy as np

from .audio_types import AudioData, Processor

# Initialize numpy to use single thread for callbacks
np.seterr(all="ignore")


class SpectrumProcessor(Processor):
    """
    Computes the FFT power spectrum with 20000 frequency elements.
    No mel filterbank applied - pure FFT analysis.
    """

    def __init__(self, chunk_size, sample_rate, sensitivity=2.0):
        super().__init__(chunk_size, sample_rate)
        self.sensitivity = sensitivity

    @staticmethod
    def hz_to_bin(freq_hz, sample_rate, chunk_size):
        return int(freq_hz * chunk_size / sample_rate)

    def process(self, data) -> AudioData:
        arr = np.asarray(data, dtype=np.float32)
        if arr.size == 0:
            return AudioData(np.zeros(self.chunk_size // 2 + 1, dtype=np.float32))

        max_abs = float(np.abs(arr).max())
        if max_abs > 1.01:
            arr = np.clip(arr, -1.0, 1.0)
        elif 0 < max_abs < 0.001:
            arr = arr / max_abs

        # Zero-pad to 4x chunk size → 4x finer frequency resolution
        # e.g. 1024 → 4096 points: 44100/4096 ≈ 10.8 Hz/bin
        fft_size = self.chunk_size * 4
        window = np.hanning(len(arr))
        arr = arr * window

        with np.errstate(all="ignore"):
            fft_result = np.fft.rfft(arr, n=fft_size)  # <-- n= is the key
            power_spectrum = np.square(np.abs(fft_result))

        p95 = np.percentile(power_spectrum, 95)
        power_spectrum = np.clip(power_spectrum, 0, p95 * 2) * self.sensitivity

        return AudioData(power_spectrum)
