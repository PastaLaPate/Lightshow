import librosa
import numpy as np
from .audio_types import AudioData, Processor


class SpectrumProcessor(Processor):
    """
    Computes the FFT power spectrum and applies a Mel filter bank,
    with support for attack, decay, and sensitivity smoothing.
    """

    def __init__(
        self, chunk_size, sample_rate, n_mels=40, attack=0.9, decay=0.5, sensitivity=1.0
    ):
        super().__init__(chunk_size, sample_rate)
        self.n_mels = n_mels
        self.attack = attack
        self.decay = decay
        self.sensitivity = sensitivity
        self.mel_filters = librosa.filters.mel(
            sr=sample_rate, n_fft=chunk_size, n_mels=n_mels
        )
        self.raw_freqs = np.fft.rfftfreq(chunk_size, d=1.0 / sample_rate)
        self.prev_mel_energies = np.zeros(n_mels)  # for smoothing

    def set_mels(self, n_mels):
        self.n_mels = n_mels
        self.prev_mel_energies = np.zeros(n_mels)
        self.mel_filters = librosa.filters.mel(
            sr=self.sample_rate, n_fft=self.chunk_size, n_mels=n_mels
        )

    def process(self, data) -> AudioData:
        # Ensure array and convert to float32; normalize integers into [-1, 1]
        arr = np.asarray(data)
        if np.issubdtype(arr.dtype, np.integer):
            maxv = np.iinfo(arr.dtype).max if arr.dtype != np.int64 else 2 ** 31 - 1
            arr = arr.astype(np.float32) / float(maxv)
        else:
            arr = arr.astype(np.float32)
            # If values look like integer range, rescale to protect against misinterpreted formats
            max_abs = np.abs(arr).max() if arr.size else 0.0
            if max_abs > 1.0:
                arr = arr / max_abs

        # Compute FFT and power spectrum
        fft_result = np.fft.rfft(arr)
        power_spectrum = np.square(np.abs(fft_result))

        # Apply Mel filterbank
        mel_energies = np.dot(self.mel_filters, power_spectrum)

        # Apply sensitivity
        mel_energies *= self.sensitivity

        # Apply attack/decay smoothing
        rising = mel_energies > self.prev_mel_energies
        self.prev_mel_energies[rising] = (
            self.attack * self.prev_mel_energies[rising]
            + (1 - self.attack) * mel_energies[rising]
        )
        self.prev_mel_energies[~rising] = (
            self.decay * self.prev_mel_energies[~rising]
            + (1 - self.decay) * mel_energies[~rising]
        )

        smoothed_mel = self.prev_mel_energies.copy()

        return AudioData(power_spectrum, smoothed_mel)
