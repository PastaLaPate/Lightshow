import librosa
import numpy as np
from .audio_types import AudioData, AudioListener, Processor

class SpectrumProcessor(Processor):
    """
    Computes the FFT power spectrum and applies a Mel filter bank.
    """
    def __init__(self, chunk_size, sample_rate, n_mels=40):
        super().__init__(chunk_size, sample_rate)
        self.n_mels = n_mels
        self.mel_filters = librosa.filters.mel(sr=sample_rate,
                                                n_fft=chunk_size,
                                                n_mels=n_mels)
        self.raw_freqs = np.fft.rfftfreq(chunk_size, d=1.0 / sample_rate)
    
    def set_mels(self, n_mels):
        self.n_mels = n_mels
        self.mel_filters = librosa.filters.mel(sr=self.sample_rate,
                                                n_fft=self.chunk_size,
                                                n_mels=n_mels)

    def process(self, data) -> AudioData:
        fft_result = np.fft.rfft(data)
        # Compute power spectrum using vectorized operations.
        power_spectrum = np.square(np.abs(fft_result))
        # Compute Mel energies by applying the filter bank.
        mel_energies = np.dot(self.mel_filters, power_spectrum)
        return AudioData(power_spectrum, mel_energies)

