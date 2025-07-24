import random
import time
import typing


from lightshow.devices.animations.AAnimation import RGB, FlickerCommand
from lightshow.devices.device import PacketData, PacketStatus, PacketType
from lightshow.devices.moving_head.animations import BreakCircleAnimation
from lightshow.devices.moving_head.animations.CircleAnimation import CircleAnimation
from lightshow.devices.moving_head.animations.ListAnimation import ListAnimation
from lightshow.devices.moving_head.moving_head_animations import (
    QUART_OUT,
    AMHAnimation,
    MHAnimationFrame,
)
from lightshow.devices.moving_head.moving_head_colors import (
    RAINBOW_KICK_COLORS,
    DEFAULT_RGBs,
    random_rainbow_color,
)

if typing.TYPE_CHECKING:
    from lightshow.devices.moving_head.moving_head import MovingHead


TRIANGLE_ANIMATION = ListAnimation(
    DEFAULT_RGBs, [0, 60, 0], [45, 90, 135], True
)  # {"base": [45, 90, 135], "top": [0, 60, 0]}
SQUARE_ANIMATION = ListAnimation(DEFAULT_RGBs, [0, 0, 60, 60], [45, 135, 135, 45], True)
CIRCLE_ANIMATION = CircleAnimation(DEFAULT_RGBs, 0.01, 45, True)
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

        self.init_lists()
        self.init_state()

    def init_lists(self):
        self.anim_list: typing.List[AMHAnimation] = [
            TRIANGLE_ANIMATION,
            SQUARE_ANIMATION,
            CIRCLE_ANIMATION,
        ]

        self.color_mode_list = [RAINBOW_KICK_COLORS, random_rainbow_color]

    def init_state(self):
        self.current_anim = random.choice(self.anim_list)
        self.color_mode = random.choice(self.color_mode_list)
        self.update_anim_color_mode()

    def update_anim_color_mode(self):
        if isinstance(self.current_anim, (ListAnimation, CircleAnimation)):
            self.current_anim.setRGB(self.color_mode)

    def randomAnimation(self):
        self.current_anim = random.choice(
            [x for x in self.anim_list if x != self.current_anim]
        )
        self.color_mode = random.choice(
            [x for x in self.color_mode_list if x != self.color_mode]
        )
        self.beats_since_anim_change = 0
        self.update_anim_color_mode()

    def handlePacket(self, packet: PacketData):
        # Change animation after 14 beats
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

    def updateFromFrame(self, frame: MHAnimationFrame):
        color = frame["rgb"]
        self.device.sendCommand(color)
        self.device.sendCommand(frame["baseServo"])
        self.device.sendCommand(frame["topServo"])

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
        else:
            self.waiting_music = False

    def handleBreak(self, packet: PacketData):
        current_time = time.time_ns()
        if packet.packet_type == PacketType.BREAK:
            if packet.packet_status == PacketStatus.OFF:
                self.breaking = False

                added_time_t = min((current_time - self.breaking_since) / 1e9 / 15, 1.0)
                added_time = (
                    self.BREAK_ADDED_TIME_CURVE(added_time_t)
                    * self.BREAK_ADDED_TIME_MAX
                )
                self.device.sendCommand(
                    FlickerCommand(RGB(255, 255, 255), (2 + added_time) * 1000)
                )
                self.next_beat_cool = (
                    current_time + added_time * 1e9
                )  # Set next cooldown to 2 seconds
                self.randomAnimation()
            else:
                self.breaking_since = current_time
                self.breaking = True

    def handleBeat(self, packet: PacketData):
        if packet.packet_status == PacketStatus.ON:
            if time.time_ns() < self.next_beat_cool:
                # Skip beat
                return False
            self.beats_since_anim_change += 1
            self.next_beat_cool += self.cooldown_time
            frame = self.current_anim.next(False)
            self.updateFromFrame(frame)
