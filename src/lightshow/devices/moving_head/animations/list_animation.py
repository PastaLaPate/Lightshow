from lightshow.devices.moving_head.types import (
    AbstractMHAnimation,
    FixtureCalibration,
    ServoAngles,
)


class ListAnimation(AbstractMHAnimation):
    NAME = "List Animation"

    def __init__(
        self,
        calibration: FixtureCalibration,
        points: list[tuple[float, float]],
        reverse_chance: float = 0.5,
    ):
        """
        Args:
            points: poses as (x, y) in normalized [-1, 1] space, where
                x is the base servo and y the top servo. One pose per beat.
            reverse_chance: probability of flipping direction after each
                full pass through the list.
        """
        super().__init__(calibration)
        if not points:
            raise ValueError("ListAnimation needs at least one point")

        self.reverse_chance = reverse_chance

        self.poses: list[ServoAngles] = [calibration.to_servo(x, y) for x, y in points]
        self.index = -1  # first beat lands on pose 0
        # self.steps_done = 0

        self.cached_pose: ServoAngles = ServoAngles(0, 0)

    @classmethod
    def from_servo_angles(
        cls,
        calibration: FixtureCalibration,
        top: list[float],
        base: list[float],
        **kwargs,
    ) -> ListAnimation:
        """Port helper: build from real angles, like the old constructor."""
        points = [calibration.from_servo(b, t) for b, t in zip(base, top)]
        return cls(calibration, points, **kwargs)

    def next(self, audio_data, tick=False, dt=0.0) -> ServoAngles:
        if tick:
            return self.cached_pose

        # Advance one pose in the current direction
        direction = -1 if self.reversed else 1
        self.index = (self.index + direction) % len(self.poses)
        pose = self.poses[self.index]

        self.cached_pose = pose

        return pose

    def reverse(self):
        super().reverse()
