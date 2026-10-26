import socket
import threading
import traceback

import requests

from lightshow.core.events import notifications
from lightshow.core.fields import (
    BoolField,
    IntField,
    RuntimeField,
    StrField,
    ValidationScheme,
)
from lightshow.core.logger import Logger
from lightshow.core.observable_model import ObservableModel
from lightshow.devices.device import (
    BaseDeviceSettings,
    OutputDevice,
)
from lightshow.devices.moving_head import MovingHeadController
from lightshow.devices.moving_head.commands import RGB, Command
from lightshow.devices.types import DeviceTypeName, PacketData, PacketStatus, PacketType

# TODO: Sync with other Device -> Mirror & Flip + Upload Firmware + Set GPIO


class MovingHeadSettings(BaseDeviceSettings):
    # Connection
    ip: str = StrField(
        "IP",
        "Connectivity",
        default="",
        placeholder="0.0.0.0",
        validation_scheme=ValidationScheme.IP,
        connected_readonly=True,
    )
    http_port: int = IntField(
        "HTTP Port",
        "Connectivity",
        default=8080,
        connected_readonly=True,
    )
    udp_port: int = IntField(
        "UDP Port",
        "Connectivity",
        default=1234,
        connected_readonly=True,
    )

    # Ranges
    min_base_angle: int = IntField(
        "Min Base Angle", category="Angles/Base", default=0, min=0, max=180
    )
    max_base_angle: int = IntField(
        "Max Base Angle", category="Angles/Base", default=180, min=0, max=180
    )

    min_top_angle: int = IntField(
        "Min Top Angle", category="Angles/Top", default=0, min=0, max=180
    )
    max_top_angle: int = IntField(
        "Max Top Angle", category="Angles/Top", default=180, min=0, max=180
    )

    # Invert
    invert_base_angle: bool = BoolField(
        "Invert Base Angle", category="Angles/Invertions", default=False
    )
    invert_top_angle: bool = BoolField(
        "Invert Top Angle", category="Angles/Invertions", default=False
    )


class MovingHeadRuntime(ObservableModel):
    current_animation: str = RuntimeField("", "Current Animation")
    current_transformer: str = RuntimeField("", "Current Transformer")
    fps: int = RuntimeField(0, "FPS")


class MovingHead(OutputDevice[MovingHeadSettings, MovingHeadRuntime]):
    BADGE_COLOR = "#af0101"
    DEVICE_TYPE_NAME = DeviceTypeName.MOVING_HEAD

    def __init__(self, config):
        super().__init__(config)
        self.logger = Logger(f"MovingHead{{{self.id}}}")

        self.socket = None
        self.packetIndex = 0

        self.manual: bool = False
        self.auto_tick = False

        self.controller = MovingHeadController(self)

        # Packet queue for async processing
        self._packet_queue = []
        self._packet_lock = threading.Lock()
        self._packet_thread = None
        self._packet_thread_running = False

    def test_connection(self) -> bool:
        try:
            result = requests.post(
                f"http://{self.config.ip}:{self.config.http_port}/resetIndexCounter",
                timeout=5,
            )
        except requests.RequestException:
            return False
        return result.status_code == 200

    def connect_socket(self):
        """Establish a persistent WebSocket connection."""
        try:
            if self.test_connection():
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket.settimeout(1)
                self.addr = (self.config.ip, self.config.udp_port)
                self.packetIndex = 0
                self.logger.info(f"Successfully tested connection to {self.config.ip}")
            else:
                raise ConnectionError("Not received resetIndex, ip problem?")
        except ConnectionError as e:
            self.logger.error(f"Error connecting to {self.config.ip}: {e}")
            notifications.error.emit(
                "Connection Error",
                f"Failed to connect to {self.config.ip}. Please check the IP address and ensure the device is powered on. Error details: {traceback.format_exc()}",
            )
            self.socket = None

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
            except ConnectionError:
                return
        try:
            if self.socket:
                self.packetIndex += 1
                self.socket.sendto(
                    (f"{self.packetIndex};{message}").encode(), self.addr
                )

        except ConnectionError as e:
            self.logger.error(f"Error sending message : {e}")
            notifications.error.emit(
                "Connection Error",
                f"Failed to send message to {self.config.ip}. Error details: {traceback.format_exc()}",
            )

    def on_config_changed(self, field: str):
        self.controller.rebuild_animations()

    def sendCommand(self, command: Command):
        # print(command.toMHCommand())
        self.send_message(command.serialize_udp())

    def sendCommands(self, commands: list[Command]):
        commands_dicts = [command.serialize_udp() for command in commands]
        self.send_message(";".join(commands_dicts))

    def on(self, packet: PacketData):
        if not self.socket:
            return

        if packet.packet_type == PacketType.MANUAL_MODE:
            self.manual = packet.packet_status == PacketStatus.ON
            return
        elif packet.packet_type == PacketType.AUTO_TICK:
            self.auto_tick = packet.packet_status == PacketStatus.ON
            return

        # Queue the packet for async processing instead of blocking
        with self._packet_lock:
            self._packet_queue.append(packet)

        return super().on(packet)
