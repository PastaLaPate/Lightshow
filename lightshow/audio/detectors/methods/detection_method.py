from abc import ABC, abstractmethod
from collections import deque

from lightshow.audio.data import AudioData


class DetectionMethod(ABC):
    def __init__(
        self,
        sensitivity: float = 1.0,
        sample_rate: int = 44100,
        chunk_size: int = 1024,
        window_size: float = 1.0,  # Number of recent frames over which to average energy in seconds.
        bin_range=[0, 2],
        cooldown_time: float = 0.25,  # Cooldown time in seconds after a detection during which no new detections can occur.
    ):

        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.chunks_per_second = sample_rate / chunk_size

        self.window_size = window_size
        self.energy_history = deque(maxlen=int(window_size * self.chunks_per_second))

        self.sensitivity = sensitivity
        self.bin_range = bin_range

        self.cooldown_frame_duration = int(cooldown_time * self.chunks_per_second)
        self.cooldown_counter = 0
        self.was_above = False

    @classmethod
    def name(cls) -> str:
        return "Abstract Detection Method"

    @abstractmethod
    def get_limit(self) -> float:
        """Return the current detection limit/threshold for visualization.

        Should be called after detect() to get the threshold used in detection.
        """
        raise NotImplementedError("Subclasses must implement get_limit method.")

    def clean(self):
        """Reset the internal state of the detector."""
        self.energy_history.clear()
        self.cooldown_counter = 0
        self.was_above = False

    def register_energy(
        self, audio_data: AudioData, append_current_energy=True
    ) -> float:
        current_energy = audio_data.get_ps_mean(self.bin_range)
        if append_current_energy:
            self.energy_history.append(current_energy)
        return current_energy

    @abstractmethod
    def detect(self, audio_data: AudioData, append_current_energy=True) -> bool:
        raise NotImplementedError("Subclasses must implement the detect method.")
