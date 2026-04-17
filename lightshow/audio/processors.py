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
        """
        Process audio data and return FFT power spectrum.

        :param data: Audio samples as array
        :return: AudioData
        """
        bin_n = self.chunk_size // 2 + 1
        try:
            # Ensure array and convert to float32; normalize integers into [-1, 1]
            arr = np.asarray(data, dtype=np.float32)

            # Ensure we have valid data
            if arr.size == 0:
                return AudioData(np.zeros(bin_n, dtype=np.float32))

            # Robust normalization for float audio
            max_abs = float(np.abs(arr).max())
            if max_abs > 1.01:
                arr = np.clip(arr, -1.0, 1.0)
            elif max_abs > 0 and max_abs < 0.001:
                arr = arr / max_abs
            window = np.hanning(len(arr))
            arr = arr * window

            # Compute FFT and power spectrum using numpy (single thread)
            with np.errstate(all="ignore"):
                fft_result = np.fft.rfft(arr)
                power_spectrum = np.square(np.abs(fft_result))

            # Apply sensitivity scaling
            p95 = np.percentile(power_spectrum, 95)
            power_spectrum = np.clip(power_spectrum, 0, p95 * 2)
            power_spectrum = power_spectrum * self.sensitivity

            return AudioData(power_spectrum)
        except Exception as e:
            import traceback

            print(f"Error in processor: {e}")
            traceback.print_exc()
            # Return empty data to prevent crash
            return AudioData(np.zeros(bin_n, dtype=np.float32))
