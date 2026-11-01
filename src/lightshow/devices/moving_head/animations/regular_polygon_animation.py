import math

from lightshow.devices.moving_head.types import (
    AbstractMHAnimation,
    FixtureCalibration,
    ServoAngles,
)


class RegularPolygonAnimation(AbstractMHAnimation):
    NAME = "Regular Polygon Animation"

    def __init__(
        self,
        calibration: FixtureCalibration,
        points_num: int = 4,
        angle_offset: float = 15,
        angle_offset_step: float = 0,
        scale: float = 1.0,
        center: tuple[float, float] = (0.0, 0.0),
    ):
        """
        Args:
            points_num: number of polygon vertices.
            angle_offset: starting rotation of the polygon, in degrees.
            angle_offset_step: degrees added to the rotation after each full
                cycle (0 = the polygon never rotates).
            scale: polygon radius in normalized space (1.0 = full range).
            center: polygon center in normalized space, (x=base, y=top).
        """
        super().__init__(calibration)

        self.points_num = points_num
        self.angle_offset = angle_offset
        self.angle_offset_step = angle_offset_step
        self.scale = scale
        self.center = center

        self.cached_pose: ServoAngles = ServoAngles(0, 0)

        self.poses: list[ServoAngles] = []
        self.index = -1  # first step lands on pose 0
        self.steps_done = 0

        self.calculateServoPoses()

    def calculateServoPoses(self):
        step = 2 * math.pi / self.points_num
        offset = math.radians(self.angle_offset)
        cx, cy = self.center

        self.poses = []
        for i in range(self.points_num):
            x = cx + self.scale * math.cos(offset + step * i)
            y = cy + self.scale * math.sin(offset + step * i)
            self.poses.append(self.calibration.to_servo(x, y))

    def next(self, audio_data, tick=False, dt=0.0) -> ServoAngles:
        if tick:
            return self.cached_pose

        # Advance one vertex in the current direction
        direction = -1 if self.reversed else 1
        self.index = (self.index + direction) % len(self.poses)
        pose = self.poses[self.index]

        self.cached_pose = pose

        # End of a full lap:  optionally rotate the polygon
        self.steps_done += 1
        if self.steps_done >= len(self.poses):
            self.steps_done = 0
            if self.angle_offset_step:
                self.angle_offset += self.angle_offset_step
                self.calculateServoPoses()

        return pose

    def reverse(self):
        super().reverse()
