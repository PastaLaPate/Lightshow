import numpy as np


class AudioData:
    """
    Audio data containing frequency spectrum (FFT) with 20000 frequency elements.
    """

    def __init__(self, frequencies):
        """
        :param frequencies: Array of 20000 frequency magnitude values from FFT
        """
        self.frequencies = frequencies

    def get_freq_mean(self, range):
        """Get mean frequency magnitude over a range of indices."""
        if len(range) > 2:
            raise ValueError("Range must be a list of two elements.")
        return np.mean(self.frequencies[range[0] : range[1]])

    # Aliases for backwards compatibility with existing detectors
    def get_ps_mean(self, range):
        """Alias for get_freq_mean (power spectrum mean)."""
        return self.get_freq_mean(range)

    def get_mel_mean(self, range):
        """Alias for get_freq_mean (mel energies are now represented by frequencies)."""
        return self.get_freq_mean(range)
