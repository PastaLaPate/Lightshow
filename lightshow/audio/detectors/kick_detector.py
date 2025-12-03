from lightshow.audio.audio_streams import AudioStreamHandler
from .spike_detector import SpikeDetector, DetectionType


class KickDetector(SpikeDetector):
    def __init__(self, AudioHandler: AudioStreamHandler):
        super().__init__(
            AudioHandler,
            2,
            20,
            [0, 2],
            DetectionType.UPPER,
            1 / 10000,
            250 / 1000,
        )
        self.was_above = False

    def detect(self, data, appendCurrentEnergy=True):
        current_energy = data.get_ps_mean(self.freq_range)
        current_diff = 0
        if len(self.energy_history) > 4:
            current_diff = (
                self.energy_history[-1] - self.energy_history[-4]
                if self.energy_history[-1] > self.energy_history[-4]
                else 0
            )

        if appendCurrentEnergy:
            self.energy_history.append(current_energy)

        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
            return False

        if len(self.energy_history) < 7:
            self.was_above = False
            return False
        avg_energy = sum(self.energy_history) / len(self.energy_history)
        limit = self.sensitivity * avg_energy

        is_above = current_diff > limit
        # Only trigger on rising edge
        if is_above and not self.was_above:
            self.cooldown_counter = self.cooldown_frame_duration
            self.was_above = True
            return True
        self.was_above = is_above
        return False
