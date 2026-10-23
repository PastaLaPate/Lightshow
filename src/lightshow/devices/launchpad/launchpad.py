import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, IntEnum
from itertools import cycle
from typing import ClassVar, Literal

import mido

from lightshow.core import config
from lightshow.core.observable_model import ObservableModel
from lightshow.devices.device import InputDevice
from lightshow.devices.moving_head.moving_head import MovingHead
from lightshow.devices.moving_head.moving_head_animation_factories import (
    AnimationFactory,
)
from lightshow.devices.moving_head.moving_head_colors import (
    BLUE_COLORS,
    RED_COLORS,
    ColorTransformer,
    RedLowsModulator,
    StartWhiteTransformer,
    ToBlackTransformer,
    random_rainbow_color,
)
from lightshow.devices.moving_head.moving_head_controller import (
    CIRCLE_ANIMATION,
    LEMNISCATE_ANIMATION,
    SQUARE_ANIMATION,
    MovingHeadController,
)
from lightshow.devices.status import DeviceStatus
from lightshow.devices.types import (
    BaseDeviceSettings,
    DeviceTypeName,
    PacketData,
    PacketStatus,
    PacketType,
)
from lightshow.gui.utils import ui_signals


# Index in panel pixels
@dataclass
class Buttons:
    # Row 1 (Top / Indices 12-15)
    COLORS_MODES: int = 12
    REVERSE_ANIM: int = 13
    FLASH_WHITE: int = 14
    FADE_BLACK: int = 15

    # Row 2 (Indices 8-11)
    ANIM_CIRCLE: int = 8
    ANIM_SQUARE: int = 9
    ANIM_LEMNISCATE: int = 10
    RED_MODULATOR: int = 11

    # Row 3 (Indices 4-7)
    AUTO_TICK: int = 4
    MANUAL_TICK: int = 5
    TOGGLE_RANDOM: int = 6
    BLACKOUT: int = 7

    # Row 4 (Bottom / Indices 0-3)
    MANUAL_MODE: int = 0
    BEAT: int = 1
    BREAK: int = 2
    FLICKER: int = 3


@dataclass(frozen=True)
class Colors:
    BRIGHT_RED: int = 5
    MID_RED: int = 6
    DARK_RED: int = 7
    BRIGHT_GREEN: int = 21
    ORANGE: int = 61
    DARK_ORANGE: int = 127
    WHITE: int = 3
    GRAY: int = 2
    DARK_GRAY: int = 1
    BLACK: int = 0
    BLUE: int = 45


# From bottom left to top right
PANELS_PIXELS = [
    [11, 12, 13, 14, 21, 22, 23, 24, 31, 32, 33, 34, 41, 42, 43, 44],
    [15, 16, 17, 18, 25, 26, 27, 28, 25, 26, 27, 28, 25, 26, 27, 28],
    [51, 52, 53, 54, 61, 62, 63, 64, 71, 72, 73, 74, 81, 82, 83, 84],
    [55, 56, 57, 58, 65, 66, 67, 68, 75, 76, 77, 78, 85, 86, 87, 88],
]


class PanelSlot:
    def __init__(self, launchpad: LaunchpadX, device_id: str, index: int) -> None:
        self.launchpad = launchpad
        self.device_id = device_id
        self.index = index
        self.note_to_idx = {note: i for i, note in enumerate(PANELS_PIXELS[index])}
        self.idx_to_note = {v: k for k, v in self.note_to_idx.items()}
        self.pressed_listeners: dict[int, list[Callable[[int], None]]] = {}
        self.released_listeners: dict[int, list[Callable[[int], None]]] = {}

    def on_pressed(self, note: int):
        idx = self.note_to_idx[note]
        if idx in self.pressed_listeners:
            [listener(idx) for listener in self.pressed_listeners[idx]]

    def on_released(self, note: int):
        idx = self.note_to_idx[note]
        if idx in self.released_listeners:
            [listener(idx) for listener in self.released_listeners[idx]]

    def watchKey(self, key: int, on_pressed: Callable, on_released: Callable):
        if key not in self.pressed_listeners:
            self.pressed_listeners[key] = [on_pressed]
        else:
            self.pressed_listeners[key].append(on_pressed)

        if key not in self.released_listeners:
            self.released_listeners[key] = [on_released]
        else:
            self.released_listeners[key].append(on_released)

    def contains(self, note: int) -> bool:
        return note in self.note_to_idx

    def set_color(
        self,
        key: int,
        color_code: int,
        mode: Literal["static", "flash", "pulse"] = "static",
    ) -> None:
        self.launchpad.set_color(self.idx_to_note[key], color_code, mode)


class ControlMode(IntEnum):
    AUTO = 0
    MANUAL = 1
    HYBRID = 2  # Receives beat, but can still control animations


class ColorModes(Enum):
    RED = RED_COLORS
    BLUE = BLUE_COLORS
    RAINBOW = random_rainbow_color
    RANDOM = 4


class MovingHeadPanelSlot(PanelSlot):
    ANIM_BUTTONS: ClassVar[dict[int, AnimationFactory]] = {
        Buttons.ANIM_CIRCLE: CIRCLE_ANIMATION,
        Buttons.ANIM_SQUARE: SQUARE_ANIMATION,
        Buttons.ANIM_LEMNISCATE: LEMNISCATE_ANIMATION,
    }

    TRANSFORMER_BUTTONS: ClassVar[dict[int, type[ColorTransformer]]] = {
        Buttons.FLASH_WHITE: StartWhiteTransformer,
        Buttons.FADE_BLACK: ToBlackTransformer,
    }

    def __init__(self, launchpad: LaunchpadX, device_id: str, index: int) -> None:
        super().__init__(launchpad, device_id, index)
        device = config.global_config.device_store.get(device_id)._device
        if not isinstance(device, MovingHead):
            raise TypeError("Created with another device than MovingHead")
        self.moving_head: MovingHead = device

        # Internal States
        self.control_mode = ControlMode.AUTO
        self.controls_mode = cycle(
            [ControlMode.AUTO, ControlMode.MANUAL, ControlMode.HYBRID]
        )
        self.color_mode = ColorModes.RANDOM
        self.colors_modes = cycle(list(ColorModes))
        self.auto_tick = False
        self.breaking = False
        self.random_anim = True

        for local_idx in self.idx_to_note:
            self.watchKey(local_idx, self._on_pressed, self._on_released)

    @property
    def ctrl(self) -> MovingHeadController:
        return self.moving_head.controller

    def _send(self, packet_type: PacketType, on: bool) -> None:
        self.moving_head.on(
            PacketData(packet_type, PacketStatus.ON if on else PacketStatus.OFF)
        )

    def _on_pressed(self, key: int):
        # --- SYSTEM BUTTONS ---
        if key == Buttons.MANUAL_MODE:
            self.control_mode = next(self.controls_mode)
            self.auto_tick = False
            self.breaking = False
            self.random_anim = True  # default
            self._send(PacketType.MANUAL_MODE, self.control_mode == ControlMode.MANUAL)
            self.update_state()
            return

        if self.control_mode == ControlMode.AUTO:
            return

        # --- ROW 1: COLORS & FLASH ---
        if key == Buttons.COLORS_MODES:
            self.color_mode = next(self.colors_modes)
            value = self.color_mode.value
            self.ctrl.set_palette(None if isinstance(value, int) else value)
            self.update_state()

        elif key == Buttons.REVERSE_ANIM:
            self.ctrl.reverse_animation()
            self.update_state()

        elif key in self.TRANSFORMER_BUTTONS:
            self.ctrl.toggle_transformer(self.TRANSFORMER_BUTTONS[key])

        # --- ROW 2: ANIMATIONS ---
        elif key in self.ANIM_BUTTONS:
            if not self.random_anim:
                self.ctrl.set_animation(self.ANIM_BUTTONS[key])

        elif key == Buttons.RED_MODULATOR:
            if not self.random_anim:
                self.ctrl.toggle_transformer(RedLowsModulator)

        # --- ROW 3: TICKING & RANDOM ---
        elif key == Buttons.AUTO_TICK:
            self.auto_tick = not self.auto_tick
            self._send(PacketType.AUTO_TICK, self.auto_tick)
            self.update_state()

        elif key == Buttons.MANUAL_TICK:
            if not self.auto_tick:
                self.moving_head.on(PacketData(PacketType.TICK, PacketStatus.ON))
                self.set_color(Buttons.MANUAL_TICK, Colors.WHITE)

        elif key == Buttons.TOGGLE_RANDOM:
            self.random_anim = not self.random_anim
            self.ctrl.disable_anim_change = not self.random_anim
            self.update_state()

        elif key == Buttons.BLACKOUT:
            self.ctrl.blackout = not self.ctrl.blackout

        # --- ROW 4: BEAT / BREAK / FLICKER ---
        elif key == Buttons.BEAT:
            if not self.breaking:
                self.set_color(Buttons.BEAT, Colors.DARK_ORANGE)
                self.moving_head.on(PacketData(PacketType.BEAT, PacketStatus.ON))

        elif key == Buttons.BREAK:
            self.breaking = not self.breaking
            self._send(PacketType.BREAK, self.breaking)
            self.update_state()

        elif key == Buttons.FLICKER:
            self.launchpad.active_effects[self.idx_to_note[key]] = "flicker"

    def _on_released(self, key: int):
        midi_note = self.idx_to_note[key]
        if key == Buttons.FLICKER and midi_note in self.launchpad.active_effects:
            del self.launchpad.active_effects[midi_note]
            self.moving_head.on(PacketData(PacketType.FLICKER, PacketStatus.OFF))

        # Reset button visual state if it was a momentary action
        self.update_state()

    def update_state(self):
        if self.control_mode == ControlMode.AUTO:
            # Global Off State
            for b in range(16):
                self.set_color(b, Colors.BLACK)
            self.set_color(Buttons.MANUAL_MODE, 5)  # Dim Red
            return

        # --- ROW 4 (Bottom) ---
        self.set_color(
            Buttons.MANUAL_MODE,
            Colors.BRIGHT_GREEN if self.control_mode == ControlMode.MANUAL else 45,
        )
        # BEAT disabled when breaking
        self.set_color(
            Buttons.BEAT, Colors.ORANGE if not self.breaking else Colors.BLACK
        )
        # BREAK pulsing
        self.set_color(
            Buttons.BREAK,
            Colors.BRIGHT_RED if self.breaking else Colors.DARK_RED,
            mode="pulse" if self.breaking else "static",
        )
        self.set_color(Buttons.FLICKER, Colors.GRAY)

        # --- ROW 3 ---
        self.set_color(
            Buttons.AUTO_TICK,
            Colors.BRIGHT_GREEN if self.auto_tick else Colors.BRIGHT_RED,
        )
        # MANUAL_TICK disabled when auto_tick enabled
        self.set_color(
            Buttons.MANUAL_TICK,
            Colors.WHITE if not self.auto_tick else Colors.DARK_GRAY,
        )
        self.set_color(
            Buttons.TOGGLE_RANDOM,
            Colors.BRIGHT_GREEN if self.random_anim else Colors.BRIGHT_RED,
        )
        self.set_color(Buttons.BLACKOUT, 0)  # Visual for "Empty/Black" button

        # --- ROW 2 (Animations) ---
        # Disabled when random anim is ON
        anim_color = Colors.BLACK if self.random_anim else Colors.GRAY
        self.set_color(Buttons.ANIM_CIRCLE, anim_color)
        self.set_color(Buttons.ANIM_SQUARE, anim_color)
        self.set_color(Buttons.ANIM_LEMNISCATE, anim_color)
        self.set_color(
            Buttons.RED_MODULATOR,
            Colors.MID_RED if not self.random_anim else Colors.BLACK,
        )

        # --- ROW 1 (Top) ---
        COLOR_MODES_COLORS = {
            ColorModes.BLUE: Colors.BLUE,
            ColorModes.RED: Colors.BRIGHT_RED,
            ColorModes.RAINBOW: Colors.WHITE,
        }
        if self.color_mode != ColorModes.RANDOM:
            self.set_color(Buttons.COLORS_MODES, COLOR_MODES_COLORS[self.color_mode])
        else:
            self.set_color(Buttons.COLORS_MODES, Colors.WHITE, mode="pulse")
        self.set_color(
            Buttons.REVERSE_ANIM,
            Colors.BRIGHT_GREEN
            if not self.ctrl.current_anim.reversed
            else Colors.BRIGHT_RED,
        )
        self.set_color(Buttons.FLASH_WHITE, Colors.WHITE)
        self.set_color(Buttons.FADE_BLACK, Colors.GRAY, mode="pulse")


class LaunchpadSettings(BaseDeviceSettings):
    pass


class LaunchpadRuntime(ObservableModel):
    pass


class LaunchpadX(InputDevice[LaunchpadSettings, LaunchpadRuntime]):
    DEVICE_TYPE_NAME = DeviceTypeName.LAUNCHPAD_X

    def __init__(self, config):

        super().__init__(config)
        self.in_port: mido.ports.BaseInput | None = None
        self.out_port: mido.ports.BaseOutput | None = None

        # State Management
        self.used_panels: dict[int, None | str] = {  # panel_id: device_id using it
            0: None,
            1: None,
            2: None,
            3: None,
        }
        self.panels_slots: dict[int, PanelSlot | None] = {
            0: None,
            1: None,
            2: None,
            3: None,
        }

        ui_signals.devices.status_changed.connect(self._on_device_status_changed)

        # Single Thread Effect Management
        self.active_effects: dict[int, str] = {}  # button_note: effect_type
        self.running = False
        self._effect_thread: threading.Thread | None = None

    def _on_device_status_changed(self, device_id: str, new_status: DeviceStatus):
        # Assign the device a panel if one is available
        if new_status == DeviceStatus.DISCONNECTED:
            if device_id in self.used_panels.values():
                panel_id = list(self.used_panels.values()).index(device_id)
                self.used_panels[panel_id] = None
                self.panels_slots[panel_id] = None
            return
        elif new_status == DeviceStatus.CONNECTING:
            return

        if not isinstance(
            config.global_config.device_store.get(device_id)._device, MovingHead
        ):  # Use _device to avoid creating if not instanced
            return

        for panel_id, d_id in self.used_panels.items():
            if d_id is None:
                self.used_panels[panel_id] = device_id
                slot = MovingHeadPanelSlot(self, device_id, panel_id)
                self.panels_slots[panel_id] = slot
                slot.update_state()
                break

    def start_effect_engine(self):
        self.running = True
        self._effect_thread = threading.Thread(target=self._effect_loop, daemon=True)
        self._effect_thread.start()

    def _effect_loop(self):
        tick_count = 0
        while self.running:
            tick_count += 1
            current_effects = list(self.active_effects.items())

            for button_note, effect_type in current_effects:
                if effect_type == "flicker":
                    target_slot = None
                    for slot in self.panels_slots.values():
                        if slot and slot.contains(button_note):
                            target_slot = slot
                            break

                    if isinstance(target_slot, MovingHeadPanelSlot):
                        self._process_flicker(
                            target_slot.moving_head, button_note, tick_count
                        )

                elif effect_type == "pulse":
                    self._process_pulse(button_note, tick_count)

            time.sleep(0.025)

    def _process_flicker(self, device: MovingHead, button: int, tick: int):
        state = tick % 2 == 0
        status = PacketStatus.ON if state else PacketStatus.OFF
        device.on(PacketData(PacketType.FLICKER, status))
        self.set_color(button, Colors.WHITE if state else Colors.DARK_GRAY)

    def _process_pulse(self, button: int, tick: int):
        # Pulse sequence: Bright -> Mid -> Dark -> Mid
        sequence = [Colors.BRIGHT_RED, Colors.MID_RED, Colors.DARK_RED, Colors.MID_RED]
        # Change color every 8 ticks (approx 200ms)
        color = sequence[(tick // 8) % len(sequence)]
        self.set_color(button, color)

    def handle_press(self, note: int):
        for panel_slot in self.panels_slots.values():
            if panel_slot and panel_slot.contains(note):
                panel_slot.on_pressed(note)
                break

    def handle_release(self, note: int):
        for panel_slot in self.panels_slots.values():
            if panel_slot and panel_slot.contains(note):
                panel_slot.on_released(note)
                break

    def init_device(self) -> bool:
        if not self.scan_for_device():
            return False
        try:
            self.in_port = mido.open_input(  # type: ignore
                self.device_name, callback=self._on_midi_receive
            )
            self.out_port = mido.open_output(self.device_name)  # type: ignore
            self.ready = True
            self.out_port.send(mido.Message("sysex", data=[0, 32, 41, 2, 12, 14, 1]))

            self.start_effect_engine()  # Start the single shared thread
            # TODO: search for existing connected moving head
            return True
        except Exception as e:  # noqa
            print(f"Error: {e}")
            return False

    def set_color(
        self,
        note: int,
        color_code: int,
        mode: Literal["static", "flash", "pulse"] = "static",
    ):
        """Uses MIDI Channels to trigger hardware-level lighting effects."""
        if not self.out_port:
            return

        # Map mode to MIDI Channel (0-indexed for mido)
        channel_map = {"static": 0, "flash": 1, "pulse": 2}
        channel = channel_map.get(mode, 0)

        # Note: Launchpad X handles the timing internally based on MIDI clock or 120bpm
        self.out_port.send(
            mido.Message("note_on", channel=channel, note=note, velocity=color_code)
        )

    def set_rgb(self, note: int, r: int, g: int, b: int):
        """
        Sends a SysEx message to set a pad to a specific RGB color.
        r, g, b values should be 0-127 (MIDI standard).
        """
        if not self.out_port:
            return

        # Header: F0h 00h 20h 29h 02h 0Ch 03h (LED lighting SysEx)
        header = [0x00, 0x20, 0x29, 0x02, 0x0C, 0x03]
        # Colourspec: 3 (RGB type), Note Index, R, G, B
        colourspec = [3, note, r, g, b]

        self.out_port.send(mido.Message("sysex", data=header + colourspec))

    def scan_for_device(self) -> bool:
        for name in mido.get_input_names():  # type: ignore
            if "Launchpad X" in name and "MIDI In" in name:
                self.device_name = name
                return True
        return False

    def disconnect(self):
        self.running = False
        if self.in_port:
            self.in_port.close()
        if self.out_port:
            self.out_port.close()
        self.ready = False

    def _on_midi_receive(self, message: mido.Message):
        if message.type == "note_on":  # type: ignore
            if message.velocity > 0:  # type: ignore
                self.handle_press(message.note)  # type: ignore
            else:
                self.handle_release(message.note)  # type: ignore

    def on_config_changed(self, field: str): ...
