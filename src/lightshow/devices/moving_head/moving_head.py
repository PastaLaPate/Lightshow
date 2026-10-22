import socket
import threading
import traceback

import requests
from pydantic import BaseModel
from PySide6.QtWidgets import QFileDialog

from lightshow.core.logger import Logger
from lightshow.devices.animations.aanimation import RGB, Command
from lightshow.devices.device import (
    BaseDeviceSettings,
    OutputDevice,
)
from lightshow.devices.fields import (
    FileSelectorField,
    IntField,
    StrField,
    ValidationScheme,
    WidgetType,
)
from lightshow.devices.moving_head.moving_head_controller import (
    MovingHeadController,
)
from lightshow.devices.types import DeviceTypeName, PacketStatus, PacketType
from lightshow.gui.utils import ui_signals


class MovingHeadSettings(BaseDeviceSettings):
    ip: str = StrField(
        "IP",
        "",
        placeholder="0.0.0.0",
        validation_scheme=ValidationScheme.IP,
        connected_readonly=True,
    )
    port: int = IntField(
        "Port",
        3000,
        connected_readonly=True,
    )
    color_test: str = StrField(
        "Color",
        widget=WidgetType.ColorPicker,
        connected_readonly=True,
    )
    file_test: str = FileSelectorField(
        "File",
        filters=[],
        file_mode=QFileDialog.FileMode.Directory,
        connected_readonly=True,
    )


class MovingHeadRuntime(BaseModel):
    pass


class MovingHead(OutputDevice[MovingHeadSettings, MovingHeadRuntime]):
    DEVICE_TYPE_NAME = DeviceTypeName.MOVING_HEAD

    def __init__(self, config):
        super().__init__(config)
        self.logger = Logger(f"MovingHead{{{self.id}}}")

        self.socket = None
        self.packetIndex = 0

        self.device_name = ""  # Eg "Living Room Moving Head"

        self.manual = False
        self.auto_tick = False
        self.current_anim = ""
        self.controller = MovingHeadController(self)
        self.base_offset = 0
        self.base_range = (0, 180)
        self.base_servo_range = f"({self.base_range[0]},{self.base_range[1]})"
        self.top_offset = 0
        self.top_range = (0, 180)
        self.top_servo_range = f"({self.top_range[0]},{self.top_range[1]})"

        # Packet queue for async processing
        self._packet_queue = []
        self._packet_lock = threading.Lock()
        self._packet_thread = None
        self._packet_thread_running = False

    def test_connection(self) -> bool:
        try:
            # TODO: move device connection to a bg thread or something
            result = requests.post(
                f"http://{self.config.ip}:81/resetIndexCounter", timeout=2
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
                self.addr = (self.config.ip, 1234)
                self.packetIndex = 0
                self.udp_address = f"{self.config.ip}:1234"
                # self.showed_props_update()
                self.logger.info(f"Successfully tested connection to {self.config.ip}")
            else:
                raise ConnectionError("Not received resetIndex, ip problem?")
        except ConnectionError as e:
            self.logger.error(f"Error connecting to {self.config.ip}: {e}")
            ui_signals.dialogs.show_error.emit(
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
            ui_signals.dialogs.show_error.emit(
                "Connection Error",
                f"Failed to send message to {self.config.ip}. Error details: {traceback.format_exc()}",
            )

    def on_config_changed(self, field: str):
        pass

    def sendCommand(self, command: Command):
        # print(command.toMHCommand())
        self.send_message(command.toUDP_MH_Command())

    def sendCommands(self, commands: list[Command]):
        commands_dicts = [command.toUDP_MH_Command() for command in commands]
        self.send_message(";".join(commands_dicts))

    def on(self, packet):
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
