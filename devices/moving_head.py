from typing import List
from .device import *
from itertools import cycle

import json
import time
import websocket  # pip install websocket-client

#
# TODO: Error connecting to ws://192.168.1.54:81/ws: [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond
# Add auto reconnect

class MovingHead(Device):
    def __init__(self):
        self.id = id(self)
        # Use the WebSocket URL (the ESP32 WebSocket server should be running on port 81)
        self.ws_url = "ws://192.168.1.54:81/ws"
        self.ws = None
        self.r, self.g, self.b = 0, 0, 0
        self.baseAngle, self.topAngle = 0, 0
        self.last_on_time = 0  # Track the last time the `on` method was called (in ns)
        self.cooldown_time = 0.2 * 1e9  # Cooldown time in nanoseconds (0.3 seconds)
        self.base_cycle = cycle([0, 90, 180])
        self.rgb_cycle = cycle([(255, 0, 0), (0, 255, 0), (0, 0, 255)])  # RGB colors for the LED
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

    def rgb(self):
        """Set the LED color via WebSocket."""
        print(f"Setting rgb to ({self.r}, {self.g}, {self.b})")
        message = {"led": {"r": self.r, "g": self.g, "b": self.b}}
        self.send_message(message)

    def baseServo(self):
        """Set the base servo angle via WebSocket."""
        print(f"Setting base servo to {self.baseAngle}")
        message = {"servo": "base", "angle": self.baseAngle}
        self.send_message(message)

    def topServo(self):
        """Set the top servo angle via WebSocket."""
        print(f"Setting top servo to {self.topAngle}")
        message = {"servo": "top", "angle": self.topAngle}
        self.send_message(message)
    
    def nextBaseAngle(self):
        self.baseAngle = next(self.base_cycle)
            
    def on(self, packet):

        if not self.ws:
            return

        """Handle a packet (e.g. beat) and update the device state accordingly."""
        current_time = time.time_ns()
        if current_time - self.last_on_time < self.cooldown_time:
            print("Cooldown active, skipping on command")
            return False  # Skip the `on` command if cooldown is active

        if packet.packet_type == PacketType.BEAT and packet.packet_status == PacketStatus.ON:
            # Change LED to red and move top servo as an example reaction
            self.r, self.g, self.b = next(self.rgb_cycle)
            self.baseAngle, self.topAngle = 0, 180 if self.topAngle == 0 else 0
            self.rgb()
            self.topServo()
            self.nextBaseAngle()
            self.baseServo()
        
        self.last_on_time = current_time  # Update the last on time
        return super().on(packet)
    
    @property
    def name(self):
        return f"MovingHead #{self.id} Connected to {self.ws_url}"
