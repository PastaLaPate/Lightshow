import librosa
import numpy as np
from .audio_types import AudioData, AudioListener, Processor


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
        fft_result = np.fft.rfft(data)
        power_spectrum = np.square(np.abs(fft_result))
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
