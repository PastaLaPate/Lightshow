from collections import deque
import random
import time
import typing

import numpy as np


from lightshow.devices.animations.AAnimation import RGB, FlickerCommand
from lightshow.devices.device import PacketData, PacketStatus, PacketType
from lightshow.devices.moving_head.animations import BreakCircleAnimation
from lightshow.devices.moving_head.animations.BernoulliLemniscateAnimation import (
    BernoulliLemniscateAnimation,
)
from lightshow.devices.moving_head.animations.CircleAnimation import CircleAnimation
from lightshow.devices.moving_head.animations.ListAnimation import ListAnimation
from lightshow.devices.moving_head.animations.RegularPolygonAnimation import (
    RegularPolygonAnimation,
)
from lightshow.devices.moving_head.moving_head_animations import (
    QUART_OUT,
    AMHAnimation,
    MHAnimationFrame,
)
from lightshow.devices.moving_head.moving_head_colors import (
    RAINBOW_KICK_COLORS,
    DEFAULT_RGBs,
    random_rainbow_color,
    startFlicker,
    toFadeBlack,
)
from lightshow.utils.config import Config

if typing.TYPE_CHECKING:
    from lightshow.devices.moving_head.moving_head import MovingHead

TRIANGLE_ANIMATION = RegularPolygonAnimation(DEFAULT_RGBs, 3, (0, 60), (45, 135))
# TRIANGLE_ANIMATION = ListAnimation(
#    DEFAULT_RGBs, [0, 60, 0], [45, 90, 135]
# )  # {"base": [45, 90, 135], "top": [0, 60, 0]}
# SQUARE_ANIMATION = ListAnimation(DEFAULT_RGBs, [0, 0, 60, 60], [45, 135, 135, 45])
SQUARE_ANIMATION = RegularPolygonAnimation(DEFAULT_RGBs, 4, (0, 60), (45, 135))
CIRCLE_ANIMATION = CircleAnimation(DEFAULT_RGBs, 0.01, 45)
LEMNISCATE_ANIMATION = BernoulliLemniscateAnimation(DEFAULT_RGBs, 0.01, 45)
CIRCLE_BREAK_ANIMATION = BreakCircleAnimation(45)


class MovingHeadController:
    def __init__(self, device: "MovingHead"):
        self.device = device
        self.waiting_music = False

        # =====================
        #      Cooldowns
        # =====================
        self.next_beat_cool = 0  # In ns Time before a new beat can be processed
        self.cooldown_time = 0.1 * 1e9  # Cooldown time in nanoseconds (0.3 seconds)

        # =====================
        #     Break related
        # =====================
        self.BREAK_ADDED_TIME_MAX = 3
        self.BREAK_ADDED_TIME_CURVE = QUART_OUT
        self.breaking = False
        self.breaking_since = 0

        self.beats_since_anim_change = 0
        self.beats_time = deque(maxlen=30)  # last 30 beats to calculate average for BPM

        self.max_fps = Config().max_fps
        self.frame_time = 1 / self.max_fps * 1e9  # For nanoseconds
        self.next_frame_time = 0
        self.avg_fps = deque(maxlen=self.max_fps * 2)

        self.init_lists()
        self.init_state()

    def init_lists(self):
        self.anim_list: typing.List[AMHAnimation] = [
            TRIANGLE_ANIMATION,
            # CIRCLE_ANIMATION,
            # LEMNISCATE_ANIMATION,
            SQUARE_ANIMATION,
        ]

        self.color_mode_list = [RAINBOW_KICK_COLORS, random_rainbow_color]

    def init_state(self):
        self.current_anim = random.choice(self.anim_list)
        self.color_mode = random.choice(self.color_mode_list)
        self.update_anim_color_mode()

    def update_anim_color_mode(self):
        if isinstance(self.current_anim, (ListAnimation, CircleAnimation)):
            self.current_anim.setRGB(self.color_mode)
        self.current_anim.setTransformer(startFlicker)
        if len(self.beats_time) > 1:
            bpm = self.calcBPM()
            if bpm < 100:
                self.current_anim.setTransformer(toFadeBlack)

    def calcBPM(self):
        # Convert nanoseconds to seconds by dividing by 1e9
        time_diffs = np.diff(self.beats_time) / 1e9
        if len(time_diffs) == 0:
            return 0  # Avoid division by zero if there are no differences
        return 60 / np.mean(time_diffs)  # Convert to BPM

    def randomAnimation(self):
        self.current_anim = random.choice(
            [x for x in self.anim_list if x != self.current_anim]
        )
        self.color_mode = random.choice(
            [x for x in self.color_mode_list if x != self.color_mode]
        )
        self.beats_since_anim_change = 0
        self.update_anim_color_mode()
        frm = self.current_anim.next(False)
        self.updateFromFrame(frm)

    def handlePacket(self, packet: PacketData):
        if self.beats_since_anim_change > 14:
            self.randomAnimation()
        match packet.packet_type:
            case PacketType.NEW_MUSIC:
                self.handleNewMusic(packet)
            case PacketType.BREAK:
                self.handleBreak(packet)

        if self.breaking or self.waiting_music:
            self.tickFillingAnim()
            return
        if self.current_anim.isTickeable():
            self.tickCurrentAnim()

        if packet.packet_type == PacketType.BEAT:
            self.handleBeat(packet)
        # Change animation after 14 beats

    def updateFromFrame(self, frame: MHAnimationFrame):
        if self.next_frame_time > time.time_ns():
            return
        self.next_frame_time = time.time_ns() + self.frame_time
        self.avg_fps.append(time.time_ns())
        color = frame["rgb"]
        self.device.sendCommand(color)
        self.device.sendCommand(frame["baseServo"])
        self.device.sendCommand(frame["topServo"])

    def calcAverageFPS(self):
        if len(self.avg_fps) < 2:
            return 0  # Not enough data to calculate FPS
        # Calculate time differences between consecutive frames (in seconds)
        time_diffs = np.diff(self.avg_fps) / 1e9
        # Calculate average FPS
        return 1 / np.mean(time_diffs)

    def tickFillingAnim(self):
        self.updateFromFrame(CIRCLE_BREAK_ANIMATION.next(True))

    def tickCurrentAnim(self):
        if time.time_ns() < self.next_beat_cool:
            # Skip tick
            return False
        self.updateFromFrame(self.current_anim.next(True))

    def handleNewMusic(self, packet: PacketData):
        if packet.packet_status == PacketStatus.ON:
            self.waiting_music = True
            self.breaking = False
            self.cooldown_time = 0
            self.beats_time.clear()
        else:
            self.waiting_music = False

    def handleBreak(self, packet: PacketData):
        current_time = time.time_ns()
        if packet.packet_type == PacketType.BREAK:
            if packet.packet_status == PacketStatus.OFF:
                self.breaking = False
                self.beats_time.extend(
                    [x + current_time - self.breaking_since for x in self.beats_time]
                )
                added_time_t = min((current_time - self.breaking_since) / 1e9 / 15, 1.0)
                added_time = (
                    self.BREAK_ADDED_TIME_CURVE(added_time_t)
                    * self.BREAK_ADDED_TIME_MAX
                )
                self.randomAnimation()
                self.device.sendCommand(
                    FlickerCommand(RGB(255, 255, 255), (2 + added_time) * 1000)
                )
                self.next_beat_cool = (
                    current_time + added_time * 1e9
                )  # Set next cooldown to 2 seconds
            else:
                self.breaking_since = current_time
                self.breaking = True

    def handleBeat(self, packet: PacketData):
        if packet.packet_status == PacketStatus.ON:
            self.beats_time.append(time.time_ns())
            if time.time_ns() < self.next_beat_cool:
                # Skip beat
                return False
            self.beats_since_anim_change += 1
            self.next_beat_cool += self.cooldown_time
            frame = self.current_anim.next(False)
            self.updateFromFrame(frame)
            bpm = self.calcBPM()
            print(f"bpm: {bpm}")
