import requests
import socket
import threading
from typing import Any, List, Literal, Tuple

from lightshow.devices.animations.AAnimation import RGB, Command
from lightshow.devices.device import Device
from lightshow.devices.moving_head.moving_head_controller import MovingHeadController
from lightshow.utils.logger import Logger

class MovingHead(Device):
    DEVICE_TYPE_NAME: Literal["LED Moving Head"] = "LED Moving Head"

    EDITABLE_PROPS = [("ip", str)]

    def __init__(self):
        self.id = id(self)
        self.logger = Logger(f"MovingHead{{{self.id}}}")
        
        self.socket = None
        self.ip = "192.168.1.XX"  # ESP32 IP
        self.addr = (self.ip, 1234)
        self.packetIndex = 0

        self.device_name = ""  # Eg "Living Room Moving Head"

        self.controller = MovingHeadController(self)
        self.base_offset = 0
        self.base_range = (0, 180)
        self.top_offset = 0
        self.top_range = (0, 180)
        
        # Packet queue for async processing
        self._packet_queue = []
        self._packet_lock = threading.Lock()
        self._packet_thread = None
        self._packet_thread_running = False

        super().__init__()

    def test_connection(self):
        result = requests.post(f"http://{self.ip}:81/resetIndexCounter")
        return result.status_code == 200
    
    def connect_socket(self):
        """Establish a persistent WebSocket connection."""
        try:
            if self.test_connection():
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket.settimeout(1)
                self.addr = (self.ip, 1234)
                self.packetIndex = 0
                self.logger.info(f"Successfully tested connection to {self.ip}")
            else:
                raise Exception("Not received resetIndex, ip problem?")
        except Exception as e:
            self.logger.error(f"Error connecting to {self.ip}: {e}")
            self.ws = None

    def disconnect(self):
        self._packet_thread_running = False
        if self._packet_thread:
            self._packet_thread.join(timeout=1)
        self.test_connection()
        return super().disconnect()

    def scan_for_device(self):
        return self.test_connection()

    def init_device(self):
        """Initialize the device state (e.g. LED and base servo)."""
        self.test_connection()
        self.connect_socket()
        self.sendCommand(RGB(255, 255, 255))
        # Start packet processing thread
        self._start_packet_thread()
        return True
    
    def _start_packet_thread(self):
        """Start the background thread for processing device packets."""
        if not self._packet_thread_running:
            self._packet_thread_running = True
            self._packet_thread = threading.Thread(
                target=self._process_packets, daemon=True
            )
            self._packet_thread.start()
    
    def _process_packets(self):
        """Background thread that processes queued packets."""
        while self._packet_thread_running:
            with self._packet_lock:
                if self._packet_queue:
                    packet = self._packet_queue.pop(0)
                else:
                    packet = None
            
            if packet:
                self.controller.handlePacket(packet)
            else:
                threading.Event().wait(0.001)  # Sleep briefly if no packets

    def send_message(self, message: str):
        """Send a JSON message over the UDP connection.

        If the connection is lost, this function will attempt to reconnect.
        """
        if not self.socket:
            try:
                self.connect_socket()
            except Exception:
                return
        try:
            if self.socket:
                self.packetIndex += 1
                self.socket.sendto((f"{self.packetIndex};{message}").encode(), self.addr)
            
        except Exception as e:
            self.logger.error(f"Error sending message : {e}")

    def sendCommand(self, command: Command):
        # print(command.toMHCommand())
        self.send_message(command.toUDP_MH_Command())

    def sendCommands(self, commands: List[Command]):
        commands_dicts = [command.toUDP_MH_Command() for command in commands]
        self.send_message(";".join(commands_dicts))

    def on(self, packet):
        if not self.socket:
            return
        
        # Queue the packet for async processing instead of blocking
        with self._packet_lock:
            self._packet_queue.append(packet)
        
        return super().on(packet)

    def save(self) -> Tuple[str, dict[str, Any]]:
        return self.DEVICE_TYPE_NAME, {
            "ip": self.ip,
            "device_name": self.device_name,
            "base_offset": self.base_offset,
            "base_range": self.base_range,
            "top_offset": self.top_offset,
            "top_range": self.top_range,
        }

    def load(self, data: Tuple[str, dict[str, Any]]) -> bool:
        name, config = data
        self.device_name = name
        self.ip = config.get("ip", self.ip)
        self.base_offset = config.get("base_offset", self.base_offset)
        self.base_range = tuple(config.get("base_range", self.base_range))
        self.top_offset = config.get("top_offset", self.top_offset)
        self.top_range = tuple(config.get("top_range", self.top_range))
        return super().load(data)

    @property
    def name(self):
        return f"MovingHead #{self.id} ({self.device_name}) Connected to {self.ip}"
