import random
import time
import typing
from collections import deque

import numpy as np

from lightshow.audio.beat_tracker import BeatTracker
from lightshow.audio.data import AudioData
from lightshow.core.logger import Logger
from lightshow.devices.animations import FadeCommand
from lightshow.devices.animations.aanimation import RGB, FlickerCommand
from lightshow.devices.device import PacketData
from lightshow.devices.moving_head.animations import (
    BernoulliLemniscateAnimation,
    BounceAnimation,
    BreakCircleAnimation,
    CircleAnimation,
    RegularPolygonAnimation,
)
from lightshow.devices.moving_head.moving_head_animation_factories import (
    AnimationFactory,
)
from lightshow.devices.moving_head.moving_head_animations import (
    QUART_OUT,
    AMHAnimation,
    ColorOnTick,
    HasPalette,
    MHAnimationFrame,
)
from lightshow.devices.moving_head.moving_head_colors import (
    COLOR_MODE,
    RAINBOW_KICK_COLORS,
    TRANSFORMERS,
    BlankTransformer,
    ColorTransformer,
    DEFAULT_RGBs,
    random_rainbow_color,
)
from lightshow.devices.types import FixtureCalibration, PacketStatus, PacketType

if typing.TYPE_CHECKING:
    from lightshow.devices.moving_head.moving_head import MovingHead

TRIANGLE_ANIMATION = lambda calib: RegularPolygonAnimation(
    calib, rgb=DEFAULT_RGBs, points_num=3
)
SQUARE_ANIMATION = lambda calib: RegularPolygonAnimation(
    calib, rgb=DEFAULT_RGBs, points_num=4
)
CIRCLE_ANIMATION = lambda calib: CircleAnimation(calib, rgb=DEFAULT_RGBs, speed=0.3)
LEMNISCATE_ANIMATION = lambda calib: BernoulliLemniscateAnimation(
    calib, rgb=DEFAULT_RGBs, speed=0.3
)
CIRCLE_BREAK_ANIMATION = lambda calib: BreakCircleAnimation(calib, hue_speed=0.5)
BOUNCE_ANIMATION = lambda calib: BounceAnimation(calib, rgb=DEFAULT_RGBs)

NS_PER_S = 1e9


def now_ns() -> int:
    return time.monotonic_ns()


DEFAULT_ANIMATIONS: tuple[AnimationFactory, ...] = (
    TRIANGLE_ANIMATION,
    CIRCLE_ANIMATION,
    LEMNISCATE_ANIMATION,
    SQUARE_ANIMATION,
    BOUNCE_ANIMATION,
)


class FrameLimiter:
    """Caps how often frames go to the fixture and tracks the achieved FPS."""

    def __init__(self, max_fps: int):
        self.min_interval_ns = NS_PER_S // max_fps
        self._next_ns = 0
        self._sent: deque[int] = deque(maxlen=max_fps * 2)

    def try_acquire(self, force: bool = False) -> bool:
        now = now_ns()
        if not force and now < self._next_ns:
            return False
        self._next_ns = now + self.min_interval_ns
        self._sent.append(now)
        return True

    @property
    def fps(self) -> float:
        if len(self._sent) < 2:
            return 0.0
        span_s = (self._sent[-1] - self._sent[0]) / NS_PER_S
        return (len(self._sent) - 1) / span_s if span_s > 0 else 0.0


class MovingHeadController:
    ANIM_CHANGE_AFTER_BEATS = 20
    BREAK_RAMP_S = 15.0  # break length at which the post-break hold is maxed out
    BREAK_ADDED_TIME_MAX = 3.0  # s
    BREAK_FLASH_MIN_NS = NS_PER_S
    FPS_REPORT_EVERY_NS = 2 * NS_PER_S

    # TODO: Add runtime schema things -> FPS tracker, current anim etc

    def __init__(self, device: MovingHead):
        from lightshow.core.config import _Settings, global_config

        self.device: MovingHead = device
        self.logger = Logger(f"MovingHeadController{{{device.id}}}")

        self.limiter = FrameLimiter(global_config.settings[_Settings.MAX_FPS] or 60)
        self.beats = BeatTracker()

        # flags
        self.blackout = False
        self.waiting_music = False
        self.breaking = False
        self.disable_anim_change = False
        self.beats_since_anim_change: int = 0
        self.current_fps: float = 0.0

        # private state
        self.BREAK_ADDED_TIME_CURVE = QUART_OUT
        self._break_started_ns: int = 0
        self._hold_until_ns: int = (
            0  # After break, due to FlickerCommand, wait until x to send frames
        )
        self._last_tick_ns: int = now_ns()
        self._last_fps_report_ns: int = 0
        self._active_oneshot: FadeCommand | FlickerCommand | None = None

        self.latest_audio_data = AudioData(np.zeros(20000))

        # animations
        self.color_mode_list: list[COLOR_MODE] = [
            RAINBOW_KICK_COLORS,
            random_rainbow_color,
        ]
        self.color_mode: COLOR_MODE = RAINBOW_KICK_COLORS
        self.break_anim: AMHAnimation = CIRCLE_BREAK_ANIMATION(self.get_calib())
        self.anim_list: list[AMHAnimation] = self._build_animations()
        self.current_anim: AMHAnimation = random.choice(self.anim_list)
        self._activate(self.current_anim)

    # animations

    def get_calib(self) -> FixtureCalibration:
        config = self.device.config
        return FixtureCalibration(
            base_range=(config.min_base_angle, config.max_base_angle),
            top_range=(config.min_top_angle, config.max_top_angle),
            invert_base=config.invert_base_angle,
            invert_top=config.invert_top_angle,
            servo_limits=(0, 180),
        )

    def _build_animations(self) -> list[AMHAnimation]:
        calib = self.get_calib()
        return [factory(calib) for factory in DEFAULT_ANIMATIONS]

    def rebuild_animations(self) -> None:
        # Called after calibration changed
        self.break_anim = CIRCLE_BREAK_ANIMATION(self.get_calib())
        self.anim_list = self._build_animations()
        self._activate(random.choice(self.anim_list))

    def randomAnimation(self) -> None:
        candidates = [a for a in self.anim_list if a is not self.current_anim]
        self._activate(random.choice(candidates or self.anim_list))
        self._send(self._advance(self.current_anim, beat=True), force=True)

    def _activate(self, anim: AMHAnimation) -> None:
        self.current_anim = anim
        self.beats_since_anim_change = 0
        self.set_palette(None)
        self.set_transformer(
            random.choice([t for t in TRANSFORMERS if t.filter()(anim)])()
        )
        self.device.runtime.current_animation = type(anim).__name__

    # public api
    def set_palette(self, color_mode: COLOR_MODE | None = None) -> None:
        """Set the palette on the current animation. None = pick a random mode."""
        if color_mode is None:
            color_mode = random.choice(self.color_mode_list)
        self.color_mode = color_mode
        if isinstance(self.current_anim, HasPalette):
            self.current_anim.setRGB(color_mode)

    def set_transformer(self, transformer: ColorTransformer) -> None:
        anim = self.current_anim
        anim.setTransformer(transformer)
        if isinstance(anim, ColorOnTick):
            # Any transformer that follows the audio updates per tick; all others
            # only on beats. Set on every swap so the flag can never go stale.
            anim.change_color_on_tick = transformer.reactive()

    def toggle_transformer(self, kind: type[ColorTransformer]) -> None:
        """Switch `kind` on, or back to Blank if it's already active."""
        active = isinstance(self.current_anim.transformer, kind)
        self.set_transformer(BlankTransformer() if active else kind())

    def set_animation(self, factory: AnimationFactory) -> None:
        """Replace the current animation, keeping the palette and transformer."""
        previous = self.current_anim
        self.current_anim = factory(self.get_calib())
        self.beats_since_anim_change = 0
        self.set_palette(self.color_mode)
        self.set_transformer(previous.transformer or BlankTransformer())
        self.device.runtime.current_animation = type(self.current_anim).__name__

    def reverse_animation(self) -> None:
        self.current_anim.reverse()

    # packets

    def handlePacket(self, packet: PacketData) -> None:

        if self._handle_flicker(packet):
            return
        if self.blackout:
            self.device.sendCommand(RGB(0, 0, 0))
            return

        if packet.audio_data:
            self.latest_audio_data = packet.audio_data

        if (
            self.beats_since_anim_change > self.ANIM_CHANGE_AFTER_BEATS
            and not self.disable_anim_change
        ):
            self.randomAnimation()

        if packet.packet_type == PacketType.NEW_MUSIC:
            self._on_new_music(packet)
        elif packet.packet_type == PacketType.BREAK:
            self._on_break(packet)

        if self.breaking or self.waiting_music:
            self._send(self._advance(self.break_anim, beat=False))
            return

        if not self._holding():
            self._send(self._advance(self.current_anim, beat=False))
        if packet.packet_type == PacketType.BEAT:
            self._on_beat(packet)

    def _handle_flicker(self, packet: PacketData) -> bool:
        # Returns if packet was handled
        if packet.packet_type != PacketType.FLICKER:
            return False
        if packet.packet_status == PacketStatus.ON:
            # Flicker for 60s (stopped manually)
            self.device.sendCommand(FlickerCommand(RGB(255, 255, 255), 60_000))
            return True
        self.device.sendCommands([RGB(0, 0, 0)])
        self._active_oneshot = None
        return False

    def _on_new_music(self, packet: PacketData) -> None:
        if packet.packet_status == PacketStatus.ON:
            self.waiting_music = True
            self.breaking = False
            self.beats.clear()
        else:
            self.waiting_music = False

    def _on_break(self, packet: PacketData) -> None:
        now = now_ns()
        if packet.packet_status == PacketStatus.ON:
            self._break_started_ns = now
            self.breaking = True
            return

        self.breaking = False
        duration_ns = now - self._break_started_ns
        self.beats.shift(duration_ns)

        ramp = min(duration_ns / NS_PER_S / self.BREAK_RAMP_S, 1.0)
        extra_s = self.BREAK_ADDED_TIME_CURVE(ramp) * self.BREAK_ADDED_TIME_MAX

        self.randomAnimation()
        if duration_ns > self.BREAK_FLASH_MIN_NS:
            self._hold_until_ns = now + int(extra_s * NS_PER_S)
            self.device.sendCommand(
                FlickerCommand(RGB(255, 255, 255), (2 + extra_s) * 1000)
            )

    def _on_beat(self, packet: PacketData) -> None:
        self._report_fps()
        if packet.packet_status == PacketStatus.OFF:
            return
        self.beats.record()
        if self._holding() or not self.beats.accept():
            return
        self.beats_since_anim_change += 1
        self._send(self._advance(self.current_anim, beat=True), force=True)

    # helpers
    @property
    def filling(self) -> bool:
        return self.breaking or self.waiting_music

    def _holding(self) -> bool:
        return now_ns() < self._hold_until_ns

    def _advance(self, anim: AMHAnimation, beat: bool) -> MHAnimationFrame:
        now = now_ns()
        dt = (now - self._last_tick_ns) / NS_PER_S
        self._last_tick_ns = now
        return anim.next(self.latest_audio_data, not beat, dt)

    def _send(self, frame: MHAnimationFrame, force: bool = False) -> None:
        # Send a frame, force ignores the limiter
        if frame["duration"] == -1:
            return
        if not self.limiter.try_acquire(force):
            return

        color = frame["rgb"]
        if isinstance(color, (FadeCommand, FlickerCommand)):
            # One-shot: send each object once, even if the animation keeps returning it
            if color is self._active_oneshot:
                color_cmds = []
            else:
                self._active_oneshot = color
                color_cmds = [color]
        else:
            color_cmds = [color]

        self.device.sendCommands([*color_cmds, frame["baseServo"], frame["topServo"]])

    def _report_fps(self) -> None:
        now = now_ns()
        if now - self._last_fps_report_ns < self.FPS_REPORT_EVERY_NS:
            return
        from lightshow.gui.main_window import UIManager

        self.current_fps = self.limiter.fps
        self._last_fps_report_ns = now
        UIManager.get().stats_panel.update_fps(self.current_fps)
