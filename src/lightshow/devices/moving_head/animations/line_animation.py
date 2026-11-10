from lightshow.devices.moving_head.types import (
    AbstractMHAnimation,
    FixtureCalibration,
    ServoAngles,
)


class LineAnimation(AbstractMHAnimation):
    NAME = "Line Animation"

    def __init__(
        self,
        calibration: FixtureCalibration,
        angle: float = 0,
        length: float = 1,
    ):
        """Instantiates a LineAnimation

        Args:
            calibration (FixtureCalibration): the fixture's calibration.
            rgb (COLOR_MODE): the animation's current rgb mode.
            angle (float, optional): The line's angle in degree 0 corresponding to horizontal. Defaults to 0.
            length (float, optional): The line's length, mirrored on each side, 1 goes to max angle on each servo. Defaults to 1.
        """
        super().__init__(calibration)

        self.damping = 3

        self.angle = angle
        self.length = length

        self.progress: float = 0
        self.velocity: float = 0
        self.target_cross_time = 0.2  # In seconds

    def next(self, audio_data, tick=False, dt=0.0) -> ServoAngles:
        if tick:
            return self.cached_pose

        # Advance one pose in the current direction
        direction = -1 if self.reversed else 1
        pose = ServoAngles(-direction, direction)
        self.cached_pose = pose

        return pose
