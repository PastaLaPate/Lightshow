import json
from typing import Any, List, Literal, Tuple
import websocket  # pip install websocket-client

from lightshow.devices.animations.AAnimation import RGB, Command
from lightshow.devices.device import Device
from lightshow.devices.moving_head.moving_head_controller import MovingHeadController


def deep_merge(dicts: List[dict]):
    def _merge(d1, d2: dict):
        result = dict(d1)
        for k, v in d2.items():
            if k in result:
                if isinstance(result[k], list) and isinstance(v, list):
                    result[k] = result[k] + v
                elif isinstance(result[k], dict) and isinstance(v, dict):
                    result[k] = _merge(result[k], v)
                else:
                    result[k] = v
            else:
                result[k] = v
        return result

    out = {}
    for d in dicts:
        out = _merge(out, d)
    return out


class MovingHead(Device):
    DEVICE_TYPE_NAME: Literal["LED Moving Head"] = "LED Moving Head"

    EDITABLE_PROPS = [("ws_url", str)]

    def __init__(self):
        self.id = id(self)
        self.ws = None
        self.ws_url = "ws://192.168.1.59:81/ws"  # ESP32 URL

        self.device_name = ""  # Eg "Living Room Moving Head"

        self.controller = MovingHeadController(self)
        self.base_offset = 0
        self.base_range = (0, 180)
        self.top_offset = 0
        self.top_range = (0, 180)

        super().__init__()

    def connect_ws(self):
        """Establish a persistent WebSocket connection."""
        try:
            self.ws = websocket.create_connection(self.ws_url)
            print(f"Connected to WebSocket server at {self.ws_url}")
        except Exception as e:
            print(f"Error connecting to {self.ws_url}: {e}")
            self.ws = None

    def disconnect(self):
        if self.ws:
            self.ws.close()
        return super().disconnect()

    def scan_for_device(self):
        self.connect_ws()
        """Optionally verify the connection is active."""
        return self.ws is not None

    def init_device(self):
        """Initialize the device state (e.g. LED and base servo)."""
        self.sendCommand(RGB(255, 255, 255))
        return True

    def send_message(self, message: dict):
        """Send a JSON message over the WebSocket connection.

        If the connection is lost, this function will attempt to reconnect.
        """
        if self.ws is None or not self.ws.connected:
            self.connect()
            if self.ws is None:
                print("Failed to connect to WebSocket, cannot send message")
                return
        try:
            self.ws.send(json.dumps(message))
        except Exception as e:
            print("Error sending message, attempting to reconnect:", e)
            self.ws.close()
            self.ws = None
            self.connect()
            if self.ws:
                try:
                    self.ws.send(json.dumps(message))
                except Exception as e:
                    print("Reconnection failed, cannot send message:", e)

    def sendCommand(self, command: Command):
        # print(command.toMHCommand())
        self.send_message(command.toMHCommand())

    def sendCommands(self, commands: List[Command]):
        commands_dicts = [command.toMHCommand() for command in commands]
        final_dict = deep_merge(commands_dicts)
        self.send_message(final_dict)

    def on(self, packet):
        if not self.ws:
            return

        self.controller.handlePacket(packet)
        return super().on(packet)

    def save(self) -> Tuple[str, dict[str, Any]]:
        return self.DEVICE_TYPE_NAME, {
            "ws_url": self.ws_url,
            "device_name": self.device_name,
            "base_offset": self.base_offset,
            "base_range": self.base_range,
            "top_offset": self.top_offset,
            "top_range": self.top_range,
        }

    def load(self, data: Tuple[str, dict[str, Any]]) -> bool:
        name, config = data
        self.device_name = name
        self.ws_url = config.get("ws_url", self.ws_url)
        self.base_offset = config.get("base_offset", self.base_offset)
        self.base_range = tuple(config.get("base_range", self.base_range))
        self.top_offset = config.get("top_offset", self.top_offset)
        self.top_range = tuple(config.get("top_range", self.top_range))
        return super().load(data)

    @property
    def name(self):
        return f"MovingHead #{self.id} ({self.device_name}) Connected to {self.ws_url}"
