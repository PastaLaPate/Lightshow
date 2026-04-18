import numpy as np

from .audio_types import AudioData, Processor

# Initialize numpy to use single thread for callbacks
np.seterr(all="ignore")


class SpectrumProcessor(Processor):
    def __init__(self, chunk_size, sample_rate, sensitivity=2.0, attack=0.9, decay=0.5):
        super().__init__(chunk_size, sample_rate)
        self.sensitivity = sensitivity
        self.attack = attack
        self.decay = decay
        self._prev = None

    @staticmethod
    def hz_to_bin(freq_hz, sample_rate, fft_size):
        return int(freq_hz * fft_size / sample_rate)

    def process(self, data) -> AudioData:
        arr = np.asarray(data, dtype=np.float32)
        if arr.size == 0:
            return AudioData(np.zeros(self.chunk_size // 2 + 1))

        max_abs = float(np.abs(arr).max())
        if max_abs > 1.01:
            arr = np.clip(arr, -1.0, 1.0)
        elif 0 < max_abs < 0.001:
            arr = arr / max_abs

        # NO window, NO zero-padding — keeps bin math identical to old code
        fft_result = np.fft.rfft(arr)
        power_spectrum = np.square(np.abs(fft_result)) * self.sensitivity

        # Restore attack/decay smoothing to preserve transients
        if self._prev is None or self._prev.shape != power_spectrum.shape:
            self._prev = power_spectrum.copy()
        rising = power_spectrum > self._prev
        self._prev[rising] = (
            self.attack * self._prev[rising]
            + (1 - self.attack) * power_spectrum[rising]
        )
        self._prev[~rising] = (
            self.decay * self._prev[~rising]
            + (1 - self.decay) * power_spectrum[~rising]
        )

        return AudioData(self._prev.copy())
