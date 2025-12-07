from itertools import cycle
from lightshow.devices.animations.AAnimation import RGB, FadeCommand
from lightshow.devices.moving_head.moving_head_animations import (
    AMHAnimation,
    BaseServoCommand,
    MHAnimationFrame,
    TopServoCommand,
)
from lightshow.devices.moving_head.moving_head_colors import COLOR_MODE


class BounceAnimation(AMHAnimation):
    NAME = "Bounce"

    def __init__(self, rgb: COLOR_MODE):
        super().__init__()

        self.tickeable = True
        self.setRGB(rgb)

        self.cycle_progress = 0.0  # 0 → left, 1 → right
        self.direction = 1  # 1 forward, -1 backward
        self.velocity = 0.0  # progress units per second

        # Cross from one side to the other in X seconds
        self.target_cross_time = 0.2  # seconds

        self.base_range = (0, 120)
        self.top_range = (0, 50)

        self.y_f = lambda x: 0.7 - 2 * (x - 0.5) ** 2
        self.color = RGB(255, 255, 255)

    def setRGB(self, rgb: COLOR_MODE):
        self.rgb = cycle(rgb) if isinstance(rgb, list) else rgb

    def _compute_required_velocity(self, dt_est=1 / 60):
        # dt_est = estimated frame dt (60 FPS default)

        if self.direction == 1:
            distance = 1.0 - self.cycle_progress
        else:
            distance = self.cycle_progress

        if distance <= 0:
            return 0.01

        T = self.target_cross_time
        d = 3.0  # damping strength
        dt = dt_est

        # Discrete damping factor per frame
        r = 1.0 - d * dt
        if r <= 0:
            # extremely high damping → fallback
            return distance / T

        N = int(T / dt)
        rN = r**N

        denom = 1.0 - rN
        if denom < 1e-6:
            return distance / T

        # Exact velocity matching your damping model
        v0 = distance * d / denom

        return v0 * 1.05  # small boost

    def next(self, isTick=False, dt=0.0) -> MHAnimationFrame:
        self.velocity *= max(0, 1.0 - 3.0 * dt)  # 3.0 = damping strength
        if isTick:
            # Damping proportional to dt (decays similarly regardless of frame rate)
            # Apply movement
            self.cycle_progress += self.direction * self.velocity * dt

            # Clamp & bounce
            if self.cycle_progress >= 1.0:
                self.cycle_progress = 1.0
                self.direction = -1
            elif self.cycle_progress <= 0.0:
                self.cycle_progress = 0.0
                self.direction = 1
        else:
            # Always reverse direction on beat
            # Compute velocity for the new direction
            if self.velocity > 0.01 and 0.4 < self.cycle_progress < 0.6:
                self.direction *= -1
            v = self._compute_required_velocity()

            if v < 0.2:
                v = 0.2

            self.velocity = v

            # Update color
            color = next(self.rgb) if isinstance(self.rgb, cycle) else self.rgb()
            self.color = self.apply_transformer(color)

        # Servo interpolation
        base_angle = int(
            (self.base_range[1] - self.base_range[0]) * self.cycle_progress
            + self.base_range[0]
        )

        top_angle = int(
            (self.top_range[1] - self.top_range[0]) * self.y_f(self.cycle_progress)
            + self.top_range[0]
        )

        # FadeCommand support
        if isinstance(self.color, FadeCommand) and isTick:
            self.color = (
                self.color.to
                if (self.color.to.r or self.color.to.g or self.color.to.b)
                else self.color.from_
            )

        return MHAnimationFrame(
            duration=0,
            rgb=self.color,
            topServo=TopServoCommand(top_angle),
            baseServo=BaseServoCommand(base_angle),
        )

    def reverse(self):
        return super().reverse()
