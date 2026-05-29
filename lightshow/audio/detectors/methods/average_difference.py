from lightshow.audio.data import AudioData
from lightshow.audio.detectors.methods.detection_method import DetectionMethod


class AverageDifference(DetectionMethod):
    def __init__(
        self,
    ):
        super().__init__(1.75, 44100, 1024, 20.0, [0, 2], 0.25)

    @classmethod
    def name(cls):
        return "Average Difference"

    def detect(self, audio_data: AudioData, append_current_energy=True):
        current_energy = self.register_energy(audio_data, append_current_energy)

        current_diff = 0
        if len(self.energy_history) > 4:
            current_diff = (
                current_energy - self.energy_history[-4]
                if current_energy > self.energy_history[-4]
                else 0
            )

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
        else:
            # logger.debug("nope")
            pass
        self.was_above = is_above
        return False

    def get_limit(self) -> float:
        """Returns sensitivity * average energy."""
        if len(self.energy_history) < 1:
            return 0
        avg_energy = sum(self.energy_history) / len(self.energy_history)
        return self.sensitivity * avg_energy
