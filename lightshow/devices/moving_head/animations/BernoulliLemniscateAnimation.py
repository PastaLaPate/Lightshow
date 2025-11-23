import numpy as np

from lightshow.devices.moving_head.animations.CircleAnimation import CircleAnimation


class BernoulliLemniscateAnimation(CircleAnimation):
    def __init__(
        self,
        rgb,
        speed=0.01,
        base_angle_offset=0,
    ):
        super().__init__(rgb, speed, base_angle_offset)
        self.boost_speed = 0.02
        self.boost_time = 20  # 10 Frames
        self.topAngleRange = (10, 40)

    def nextCurve(self, t):
        """
        Calculates the servo angles for a Lemniscate of Bernoulli curve.
        The parametric equations are:
        x(t) = a * cos(t) / (1 + sin^2(t))
        y(t) = a * sin(t)cos(t) / (1 + sin^2(t))
        """
        # Parametric values for the lemniscate (with a=1)
        x_lemniscate = np.cos(t) / (1 + np.sin(t) ** 2)
        y_lemniscate = (np.sin(t) * np.cos(t)) / (1 + np.sin(t) ** 2)

        # Normalize x from its native range [-1, 1] to [0, 1]
        base_progress = (x_lemniscate + 1) / 2

        # Normalize y from its native range [-sqrt(2)/4, sqrt(2)/4] to [0, 1]
        max_y_val = np.sqrt(2) / 4
        top_progress = (y_lemniscate + max_y_val) / (2 * max_y_val)

        # Scale the normalized [0, 1] progress to the specified servo angle ranges
        base = self.baseAngleRange[0] + self.baseAngleRange[1] * base_progress
        top = self.topAngleRange[0] + self.topAngleRange[1] * top_progress

        return (base, top)

    def reverse(self):
        # DO NOT REVERSE
        pass
