from typing import List
from .device import *
from itertools import cycle

import numpy as np
import json
import time
import websocket  # pip install websocket-client
import random

#
# TODO: Error connecting to ws://192.168.1.54:81/ws: [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond
# Add auto reconnect

TRIANGLE_ANIMATION = {"base": [45, 90, 135], "top": [0, 60, 0]}
SQUARE_ANIMATION = {
    "base": [45, 90, 90, 45],
    "top": [0, 0, 60, 60],
}
CIRCLE_ANIMATION = {
    "base": lambda t: 45 + 45 * np.cos(t * 2 * np.pi),  # Max 0° to 90°
    "top": lambda t: 52.5 + 22.5 * np.sin(t * 2 * np.pi),  # Max 30 to 75
}

RAINBOW_KICK_COLORS = [
    (148, 0, 211),  # Violet
    (75, 0, 130),  # Indigo
    (0, 0, 255),  # Blue
    (0, 255, 0),  # Green
    (255, 255, 0),  # Yellow
    (255, 127, 0),  # Orange
    (255, 0, 0),  # Red
]


class MovingHead(Device):
    def __init__(self):
        self.id = id(self)
        # Use the WebSocket URL (the ESP32 WebSocket server should be running on port 81)
        self.ws_url = "ws://localhost:8765"
        self.ws = None
        self.r, self.g, self.b = 0, 0, 0
        self.baseAngle, self.topAngle = 0, 0
        self.next_cool = 0  # Track the next cooldown time (in ns)
        self.cooldown_time = 0.1 * 1e9  # Cooldown time in nanoseconds (0.3 seconds)

        self.anim_cycle = cycle([TRIANGLE_ANIMATION, SQUARE_ANIMATION])

        self.base_cycle = cycle(TRIANGLE_ANIMATION["base"])
        self.top_cycle = cycle(TRIANGLE_ANIMATION["top"])

        def random_rainbow_color():
            return [x * 255 for x in self.hsv_to_rgb(random.uniform(0, 1), 1, 1, 1)[:3]]

        self.rainbow_kick_colors_cycle = cycle(RAINBOW_KICK_COLORS)
        self.colors_mode = cycle(
            [lambda: next(self.rainbow_kick_colors_cycle), random_rainbow_color]
        )
        self.color_mode = next(self.colors_mode)

        self.breaking = False
        self.break_time = 0
        self.waiting_music = False
        self.break_hue = 0  # Max 1
        self.circle_progress = 0
        # Quart out
        self.break_added_time_curve = lambda t: 1 - (1 - t) ** 4

        super().__init__(False)

    def connect(self):
        """Establish a persistent WebSocket connection."""
        try:
            self.ws = websocket.create_connection(self.ws_url)
            print(f"Connected to WebSocket server at {self.ws_url}")
        except Exception as e:
            print(f"Error connecting to {self.ws_url}: {e}")
            self.ws = None

    def scan_for_device(self):
        self.connect()
        """Optionally verify the connection is active."""
        return self.ws is not None

    def init_device(self):
        """Initialize the device state (e.g. LED and base servo)."""
        self.rgb()
        self.baseServo()
        return True

    def send_message(self, message: dict):
        """Send a JSON message over the WebSocket connection.

        If the connection is lost, this function will attempt to reconnect.
        """
        if self.ws is None:
            self.connect()
            if self.ws is None:
                print("Failed to connect to WebSocket, cannot send message")
                return
        try:
            self.ws.send(json.dumps(message))
        except Exception as e:
            print("Error sending message, attempting to reconnect:", e)
            self.ws = None
            self.connect()
            if self.ws:
                try:
                    self.ws.send(json.dumps(message))
                except Exception as e:
                    print("Reconnection failed, cannot send message:", e)

    def flicker(self, duration: float = 0.1):
        """Flicker the LED for a specified duration. Color: white. Duration in seconds."""
        if self.ws is None:
            return
        else:
            duration = duration * 1000
            self.r, self.g, self.b = 255, 255, 255
            self.send_message(
                {"led": {"r": self.r, "g": self.g, "b": self.b}, "flicker": duration}
            )

    def rgb(self):
        """Set the LED color via WebSocket."""
        # print(f"Setting rgb to ({self.r}, {self.g}, {self.b})")
        message = {"led": {"r": int(self.r), "g": int(self.g), "b": int(self.b)}}
        self.send_message(message)

    def rgb_fade(self, fr: int, fg: int, fb: int, duration: float = 0.1):
        message = {
            "led": {
                "r": int(self.r),
                "g": int(self.g),
                "b": int(self.b),
            },
            "fade": duration * 1000,
            "from": {
                "r": fr,
                "g": fg,
                "b": fb,
            },
        }
        self.send_message(message)

    def baseServo(self):
        """Set the base servo angle via WebSocket."""
        # print(f"Setting base servo to {self.baseAngle}")
        message = {"servo": "base", "angle": self.baseAngle}
        self.send_message(message)

    def topServo(self):
        """Set the top servo angle via WebSocket."""
        # print(f"Setting top servo to {self.topAngle}")
        message = {"servo": "top", "angle": self.topAngle}
        self.send_message(message)

    def randomAnimation(self):
        anim = next(self.anim_cycle)
        self.base_cycle = cycle(anim["base"])
        self.top_cycle = cycle(anim["top"])

    def on(self, packet):
        if not self.ws:
            return

        """Handle a packet (e.g. beat) and update the device state accordingly."""
        current_time = time.time_ns()

        if packet.packet_type == PacketType.NEW_MUSIC:
            if packet.packet_status == PacketStatus.ON:
                self.waiting_music = True
                self.breaking = False
                self.cooldown_time = 0
            else:
                self.waiting_music = False

        if packet.packet_type == PacketType.BREAK:
            if packet.packet_status == PacketStatus.OFF:
                max_added_time = 3
                t = min((current_time - self.break_time) / 1e9 / 15, 1.0)
                added_time = self.break_added_time_curve(t) * max_added_time
                self.flicker(2 + added_time)
                self.next_cool = (
                    current_time + added_time * 1e9
                )  # Set next cooldown to 2 seconds
                self.color_mode = next(self.colors_mode)
                self.breaking = False
                self.randomAnimation()
            else:
                self.break_time = current_time
                self.breaking = True

        if self.breaking or self.waiting_music:
            # Rainbow cycle during break
            self.break_hue += 2 / 255
            if self.break_hue > 1:
                self.break_hue = 0
            self.r, self.g, self.b = [
                x * 255 for x in self.hsv_to_rgb(self.break_hue, 1, 1, 1)[:3]
            ]
            self.circle_progress += 0.01
            self.circle_progress %= 1  # Keep it in [0, 1]
            self.baseAngle = CIRCLE_ANIMATION["base"](self.circle_progress)
            self.topAngle = CIRCLE_ANIMATION["top"](self.circle_progress)
            self.rgb()
            self.baseServo()
            self.topServo()
            return super().on(packet)

        if (
            packet.packet_type == PacketType.BEAT
            and packet.packet_status == PacketStatus.ON
        ):
            if current_time < self.next_cool:
                print("Cooldown active, skipping on command")
                return False  # Skip the `on` command if cooldown is active

            # Change LED to red and move top servo as an example reaction
            fr, fg, fb = 255, 255, 255
            self.r, self.g, self.b = self.color_mode()
            self.baseAngle = next(self.base_cycle)
            self.topAngle = next(self.top_cycle)
            self.rgb_fade(fr, fg, fb, 0.2)
            self.baseServo()
            self.topServo()
        return super().on(packet)

    @property
    def name(self):
        return f"MovingHead #{self.id} Connected to {self.ws_url}"
