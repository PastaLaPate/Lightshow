import threading
import time
from dataclasses import dataclass
from typing import Literal

import mido

from lightshow.devices.device import InputDevice, PacketData, PacketStatus, PacketType
from lightshow.devices.devices_types import DeviceTypeName


@dataclass
class Buttons:
    MANUAL_MODE: int = 11
    AUTO_TICK: int = 21
    BEAT: int = 12
    TICK: int = 22
    FLICKER: int = 31


@dataclass(frozen=True)
class Colors:
    BRIGHT_RED: int = 5
    BRIGHT_GREEN: int = 21
    ORANGE: int = 61
    DARK_ORANGE: int = 127
    WHITE: int = 3
    GRAY: int = 2
    DARK_GRAY: int = 1


class LaunchpadX(InputDevice):
    DEVICE_TYPE_NAME: Literal["Novation Launchpad X"] = DeviceTypeName.LAUNCHPAD_X.value

    SHOWED_PROPS = []
    EDITABLE_PROPS = []

    def __init__(self):
        super().__init__()
        self.in_port: mido.ports.BaseInput | None = None
        self.out_port: mido.ports.BaseOutput | None = None
        self.device_name = "Not Connected"

        self.auto_tick = False
        self.manual_mode = False
        self.is_flickering = False
        self._flicker_thread: threading.Thread | None = None

        self.packet_signal = self.signals.onPacket

    def scan_for_device(self) -> bool:
        inputs = mido.get_input_names()  # type: ignore As mido has no typing
        # On Linux, we want the "MIDI In" port (usually index 1)
        for name in inputs:
            if "Launchpad X" in name and "MIDI In" in name:
                self.device_name = name
                return True
        return False

    def _flicker_loop(self):
        """Background loop to send flicker packets."""
        state = True
        while self.is_flickering:
            status = PacketStatus.ON if state else PacketStatus.OFF
            self.packet_signal.emit(PacketData(PacketType.FLICKER, status))

            # Visual feedback on the Launchpad
            color = Colors.WHITE if state else Colors.DARK_GRAY
            self.set_color(Buttons.FLICKER, color)

            state = not state
            time.sleep(0.025)  # Adjust for flicker speed (0.05s = 20Hz)

        self.packet_signal.emit(PacketData(PacketType.FLICKER, PacketStatus.OFF))
        self.update_state()

    def init_device(self) -> bool:
        """Opens ports and sets up the event callback."""
        if not self.device_name or self.device_name == "Not Connected":
            if not self.scan_for_device():
                return False

        try:
            self.in_port = mido.open_input(  # type: ignore As mido has no typing
                self.device_name, callback=self._on_midi_receive
            )
            # Match the output port to the input port
            self.out_port = mido.open_output(self.device_name)  # type: ignore As mido has no typing
            self.ready = True

            # Switch Launchpad X to Programmer Mode (Required for custom colors/grid)
            # SysEx: 240, 0, 32, 41, 2, 12, 14, 1, 247
            self.out_port.send(mido.Message("sysex", data=[0, 32, 41, 2, 12, 14, 1]))  # type: ignore As mido has no typing
            self.update_state()
            return True
        except Exception as e:
            print(f"Failed to init Launchpad: {e}")
            return False

    def _on_midi_receive(self, message: mido.Message):
        """Internal callback: This is your event handler."""
        if message.type == "note_on" and message.velocity > 0:  # type: ignore As mido has no typing
            self.handle_press(message.note)  # type: ignore As mido has no typing
        elif (
            message.type == "note_on" and message.velocity == 0  # type: ignore As mido has no typing
        ) or message.type == "note_off":  # type: ignore As mido has no typing
            self.handle_release(message.note)  # type: ignore As mido has no typing

    def handle_press(self, note: int):
        """Override this or bind functions here."""
        # print(f"Button {note} pressed!")
        if note == Buttons.MANUAL_MODE:
            self.manual_mode = not self.manual_mode
            if self.manual_mode:
                self.auto_tick = False
                self.packet_signal.emit(
                    PacketData(PacketType.MANUAL_MODE, PacketStatus.ON)
                )
                self.packet_signal.emit(
                    PacketData(PacketType.AUTO_TICK, PacketStatus.OFF)
                )
            else:
                self.auto_tick = False
                self.packet_signal.emit(
                    PacketData(PacketType.MANUAL_MODE, PacketStatus.ON)
                )
                self.packet_signal.emit(
                    PacketData(PacketType.AUTO_TICK, PacketStatus.OFF)
                )
            self.update_state()

        if note == Buttons.FLICKER and self.manual_mode:
            if not self.is_flickering:
                self.is_flickering = True
                self._flicker_thread = threading.Thread(
                    target=self._flicker_loop, daemon=True
                )
                self._flicker_thread.start()

        if note == Buttons.AUTO_TICK and self.manual_mode:
            self.auto_tick = not self.auto_tick
            self.packet_signal.emit(
                PacketData(
                    PacketType.AUTO_TICK,
                    PacketStatus.ON if self.auto_tick else PacketStatus.OFF,
                )
            )
            self.update_state()

        if note == Buttons.BEAT and self.manual_mode:
            self.set_color(Buttons.BEAT, Colors.DARK_ORANGE)
            self.packet_signal.emit(PacketData(PacketType.BEAT, PacketStatus.ON))

        if note == Buttons.TICK and self.manual_mode and not self.auto_tick:
            self.set_color(Buttons.TICK, Colors.GRAY)
            self.packet_signal.emit(PacketData(PacketType.TICK, PacketStatus.ON))

    def handle_release(self, note: int):
        """Override this or bind functions here."""
        if note == Buttons.FLICKER:
            self.is_flickering = False
        self.set_color(note, 0)
        self.update_state()

    def set_color(self, note: int, color_code: int):
        """Helper to set button colors without boilerplate."""
        if self.out_port:
            self.out_port.send(mido.Message("note_on", note=note, velocity=color_code))

    def update_state(self):
        if self.manual_mode:
            self.set_color(Buttons.MANUAL_MODE, Colors.BRIGHT_GREEN)
            self.set_color(Buttons.BEAT, Colors.ORANGE)
            self.set_color(
                Buttons.FLICKER, Colors.WHITE if self.is_flickering else Colors.GRAY
            )
            if self.auto_tick:
                self.set_color(Buttons.AUTO_TICK, Colors.BRIGHT_GREEN)
                self.set_color(Buttons.TICK, Colors.DARK_GRAY)
            else:
                self.set_color(Buttons.AUTO_TICK, Colors.BRIGHT_RED)
                self.set_color(Buttons.TICK, Colors.WHITE)
        else:
            self.set_color(Buttons.MANUAL_MODE, 5)
            for b in [Buttons.BEAT, Buttons.TICK, Buttons.AUTO_TICK, Buttons.FLICKER]:
                self.set_color(b, 0)

    def disconnect(self):
        if self.in_port:
            self.in_port.close()
        if self.out_port:
            # Set back to Live mode before leaving (Optional)
            self.out_port.send(mido.Message("sysex", data=[0, 32, 41, 2, 12, 14, 0]))
            self.out_port.close()
        self.ready = False

    def save(self):
        return self.DEVICE_TYPE_NAME, {}

    def load(self, data):
        return True

    @property
    def name(self):
        status = "Connected" if self.ready else "Disconnected"
        return f"LaunchpadX ({status})"
