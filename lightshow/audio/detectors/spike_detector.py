from collections import deque
from enum import Enum

from lightshow.audio.audio_streams import AudioCapture, AudioStreamHandler
from lightshow.audio.audio_types import AudioData


class DetectionType(Enum):
    UPPER = 0
    LOWER = 1


class SpikeDetector:
    """
    Detects spikes on audio by comparing the current low-frequency energy (e.g., average of first 3 FFT bins)
    to a moving average over a short window.
    """

    def __init__(
        self,
        AudioHandler: AudioStreamHandler,
        sensitivity=2.0,
        window_size=1,
        freq_range=[0, 3],
        detection_type=DetectionType.UPPER,
        min_duration=50 / 1000,
        cooldown=300 / 1000,
    ):  #
        """
        :param sensitivity: Factor by which the current energy must exceed the average to trigger the smaller the more sensitive.
        :param window_size: Number of recent frames over which to average energy in seconds.
        """
        AudioHandler.add_device_change_listener(self.on_device_change)
        chunks_per_second = int(
            44100 / 1024
        )  # Default value, will be updated on device change
        if not chunks_per_second or chunks_per_second <= 0:
            raise ValueError("Chunks per second must be a positive non-nul int.")
        self.chunks_per_second = chunks_per_second
        self.sensitivity = sensitivity
        self.p_window_size = window_size
        self.window_size = int(window_size * chunks_per_second)
        self.energy_history = deque(maxlen=self.window_size)
        self.freq_range = freq_range
        self.detection_type = detection_type
        self.detecting = False
        self.p_min_frame_duration = min_duration
        self.min_frame_duration = int(min_duration * chunks_per_second)
        self.current_frame_dur = 0
        self.p_cooldown = cooldown
        self.cooldown_frame_duration = max(1, int(cooldown * chunks_per_second))
        self.cooldown_counter = 0

    def on_device_change(self, device: AudioCapture):
        self.chunks_per_second = int(device.sample_rate / device.chunk_size)
        self.window_size = int(self.p_window_size * self.chunks_per_second)
        self.energy_history = deque(maxlen=self.window_size)
        self.min_frame_duration = int(
            self.p_min_frame_duration * self.chunks_per_second
        )
        self.cooldown_frame_duration = max(
            1, int(self.p_cooldown * self.chunks_per_second)
        )
        self.cooldown_counter = 0

    def clear(self):
        self.energy_history.clear()

    def detect(self, data: AudioData, appendCurrentEnergy=True):
        current_energy = data.get_ps_mean(self.freq_range)
        if appendCurrentEnergy:
            self.energy_history.append(current_energy)
        if len(self.energy_history) < 1:
            return False
        avg_energy = sum(self.energy_history) / len(self.energy_history)
        limit = self.sensitivity * avg_energy
        result = (
            current_energy > limit
            if (self.detection_type == DetectionType.UPPER)
            else current_energy < limit
        )

        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
            return False

        if not result:
            self.detecting = False
            self.current_frame_dur = 0
            return False
        elif result and not self.detecting:
            self.detecting = True
            if self.min_frame_duration == 0:
                self.detecting = False
                self.cooldown_counter = self.cooldown_frame_duration
                return True
            return False
        elif result and self.detecting:
            self.current_frame_dur += 1
            if self.current_frame_dur >= self.min_frame_duration:
                self.detecting = False
                self.current_frame_dur = 0
                self.cooldown_counter = self.cooldown_frame_duration
                return True
            else:
                return False
        else:
            return False
