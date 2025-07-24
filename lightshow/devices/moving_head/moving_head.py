import json
import websocket  # pip install websocket-client


from lightshow.devices.animations.AAnimation import RGB, Command
from lightshow.devices.device import Device
from lightshow.devices.moving_head.moving_head_controller import MovingHeadController


class MovingHead(Device):
    def __init__(self):
        self.id = id(self)
        self.ws = None
        self.ws_url = "ws://localhost:8765"  # ESP32 URL

        self.controller = MovingHeadController(self)

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
        self.sendCommand(RGB(255, 255, 255))
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

    def sendCommand(self, command: Command):
        # print(command.toMHCommand())
        self.send_message(command.toMHCommand())

    def on(self, packet):
        if not self.ws:
            return

        self.controller.handlePacket(packet)
        return super().on(packet)

    @property
    def name(self):
        return f"MovingHead #{self.id} Connected to {self.ws_url}"
