import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Literal

import mido

from lightshow.devices.device import InputDevice, PacketData, PacketStatus, PacketType
from lightshow.devices.devices_types import DeviceTypeName
from lightshow.devices.moving_head.moving_head import MovingHead
from lightshow.devices.moving_head.moving_head_animations import AMHAnimation
from lightshow.devices.moving_head.moving_head_colors import (
    BLUE_COLORS,
    RED_COLORS,
    RedLowsModulator,
    StartWhiteTransformer,
    ToBlackTransformer,
)
from lightshow.devices.moving_head.moving_head_controller import (
    CIRCLE_ANIMATION,
    LEMNISCATE_ANIMATION,
    SQUARE_ANIMATION,
)
from lightshow.utils import config


# Index in panel pixels
@dataclass
class Buttons:
    # Row 1 (Top / Indices 12-15)
    COLOR_RED: int = 12
    COLOR_BLUE: int = 13
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
        self.pressed_listeners: Dict[int, List[Callable[[int], None]]] = {}
        self.released_listeners: Dict[int, List[Callable[[int], None]]] = {}

    def on_pressed(self, note: int):
        idx = self.note_to_idx[note]
        if idx in self.pressed_listeners.keys():
            [listener(idx) for listener in self.pressed_listeners[idx]]

    def on_released(self, note: int):
        idx = self.note_to_idx[note]
        if idx in self.released_listeners.keys():
            [listener(idx) for listener in self.released_listeners[idx]]

    def watchKey(self, key: int, on_pressed: Callable, on_released: Callable):
        if key not in self.pressed_listeners.keys():
            self.pressed_listeners[key] = [on_pressed]
        else:
            self.pressed_listeners[key].append(on_pressed)

        if key not in self.released_listeners.keys():
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


class MovingHeadPanelSlot(PanelSlot):
    def __init__(self, launchpad: LaunchpadX, device_id: str, index: int) -> None:
        super().__init__(launchpad, device_id, index)
        device = config.live_devices[device_id]
        if not isinstance(device, MovingHead):
            raise Exception("Created with another device than MovingHead")
        self.moving_head: MovingHead = device

        # Internal States
        self.manual_mode = False
        self.auto_tick = False
        self.breaking = False
        self.random_anim = True

        for local_idx in self.idx_to_note.keys():
            self.watchKey(local_idx, self._on_pressed, self._on_released)

    def set_current_anim(self, anim: AMHAnimation):
        transformer = self.moving_head.controller.current_anim.transformer
        color_mode = self.moving_head.controller.current_anim.color_mode
        self.moving_head.controller.current_anim = anim
        if transformer:
            self.moving_head.controller.current_anim.setTransformer(transformer)
            if self.moving_head.controller._is_circle_animation(
                self.moving_head.controller.current_anim
            ):
                self.moving_head.controller.current_anim.change_color_on_tick = (  # type: ignore
                    isinstance(
                        self.moving_head.controller.current_anim.transformer,
                        RedLowsModulator,
                    )
                )
        self.moving_head.controller.color_mode = color_mode
        self.moving_head.controller.update_anim_color_mode()

    def _on_pressed(self, key: int):
        # --- SYSTEM BUTTONS ---
        if key == Buttons.MANUAL_MODE:
            self.manual_mode = not self.manual_mode
            self.auto_tick = False
            self.breaking = False
            self.random_anim = True  # default
            self.moving_head.on(
                PacketData(
                    PacketType.MANUAL_MODE,
                    PacketStatus.ON if self.manual_mode else PacketStatus.OFF,
                )
            )
            self.update_state()
            return

        if not self.manual_mode:
            return

        # --- ROW 1: COLORS & FLASH ---
        if key == Buttons.COLOR_RED:
            self.moving_head.controller.current_anim.setRGB(RED_COLORS)
        elif key == Buttons.COLOR_BLUE:
            self.moving_head.controller.current_anim.setRGB(BLUE_COLORS)
        elif key == Buttons.FLASH_WHITE:
            self.moving_head.controller.current_anim.setTransformer(
                StartWhiteTransformer()
            )
        elif key == Buttons.FADE_BLACK:
            self.moving_head.controller.current_anim.setTransformer(
                ToBlackTransformer()
            )
        elif key in [
            Buttons.ANIM_CIRCLE,
            Buttons.ANIM_SQUARE,
            Buttons.ANIM_LEMNISCATE,
            Buttons.RED_MODULATOR,
        ]:
            if not self.random_anim:
                if key == Buttons.ANIM_CIRCLE:
                    self.set_current_anim(CIRCLE_ANIMATION)
                elif key == Buttons.ANIM_SQUARE:
                    self.set_current_anim(SQUARE_ANIMATION)
                elif key == Buttons.ANIM_LEMNISCATE:
                    self.set_current_anim(LEMNISCATE_ANIMATION)
                elif key == Buttons.RED_MODULATOR:
                    self.moving_head.controller.current_anim.setTransformer(
                        RedLowsModulator()
                    )
                    if self.moving_head.controller._is_circle_animation(
                        self.moving_head.controller.current_anim
                    ):
                        self.moving_head.controller.current_anim.change_color_on_tick = (  # type: ignore
                            True
                        )

        # --- ROW 3: TICKING & RANDOM ---
        elif key == Buttons.AUTO_TICK:
            self.auto_tick = not self.auto_tick
            self.moving_head.on(
                PacketData(
                    PacketType.AUTO_TICK,
                    PacketStatus.ON if self.auto_tick else PacketStatus.OFF,
                )
            )
            self.update_state()

        elif key == Buttons.MANUAL_TICK:
            if not self.auto_tick:
                self.moving_head.on(PacketData(PacketType.TICK, PacketStatus.ON))
                self.set_color(Buttons.MANUAL_TICK, Colors.WHITE)

        elif key == Buttons.TOGGLE_RANDOM:
            self.random_anim = not self.random_anim
            self.moving_head.controller.disable_anim_change = not self.random_anim
            self.update_state()

        elif key == Buttons.BLACKOUT:
            self.moving_head.controller.blackout = (
                not self.moving_head.controller.blackout
            )

        # --- ROW 4: BEAT / BREAK / FLICKER ---
        elif key == Buttons.BEAT:
            if not self.breaking:
                self.set_color(Buttons.BEAT, Colors.DARK_ORANGE)
                self.moving_head.on(PacketData(PacketType.BEAT, PacketStatus.ON))

        elif key == Buttons.BREAK:
            self.breaking = not self.breaking
            self.moving_head.on(
                PacketData(
                    PacketType.BREAK,
                    PacketStatus.ON if self.breaking else PacketStatus.OFF,
                )
            )
            self.update_state()

        elif key == Buttons.FLICKER:
            self.launchpad.active_effects[self.idx_to_note[key]] = "flicker"

    def _on_released(self, key: int):
        midi_note = self.idx_to_note[key]
        if key == Buttons.FLICKER:
            if midi_note in self.launchpad.active_effects:
                del self.launchpad.active_effects[midi_note]
                self.moving_head.on(PacketData(PacketType.FLICKER, PacketStatus.OFF))

        # Reset button visual state if it was a momentary action
        self.update_state()

    def update_state(self):
        if not self.manual_mode:
            # Global Off State
            for b in range(16):
                self.set_color(b, Colors.BLACK)
            self.set_color(Buttons.MANUAL_MODE, 5)  # Dim Red
            return

        # --- ROW 4 (Bottom) ---
        self.set_color(Buttons.MANUAL_MODE, Colors.BRIGHT_GREEN)
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
        self.set_color(Buttons.COLOR_RED, Colors.BRIGHT_RED)
        self.set_color(Buttons.COLOR_BLUE, 45)
        self.set_color(Buttons.FLASH_WHITE, Colors.WHITE)
        self.set_color(Buttons.FADE_BLACK, Colors.GRAY, mode="pulse")


class LaunchpadX(InputDevice):
    DEVICE_TYPE_NAME: Literal["Novation Launchpad X"] = DeviceTypeName.LAUNCHPAD_X.value

    def __init__(self):
        from lightshow.gui.main_window import UIManager

        super().__init__()
        self.in_port: mido.ports.BaseInput | None = None
        self.out_port: mido.ports.BaseOutput | None = None
        self.device_name = "Not Connected"
        UIManager.get().ui_signals.finish_connection.connect(self._on_device_connected)
        UIManager.get().device_details.register(
            "connect_clicked", self._connect_device_callback
        )
        # State Management
        self.used_panels: Dict[int, None | str] = {  # panel_id: device_id using it
            0: None,
            1: None,
            2: None,
            3: None,
        }
        self.panels_slots: Dict[int, PanelSlot | None] = {
            0: None,
            1: None,
            2: None,
            3: None,
        }

        # Single Thread Effect Management
        self.active_effects: Dict[int, str] = {}  # button_note: effect_type
        self.running = False
        self._effect_thread: threading.Thread | None = None

    def _on_device_connected(self, device_id: str):
        # Assign the device a panel if one is available
        if not isinstance(config.live_devices[device_id], MovingHead):
            return
        for panel_id, d_id in self.used_panels.items():
            if d_id is None:
                self.used_panels[panel_id] = device_id
                slot = MovingHeadPanelSlot(self, device_id, panel_id)
                self.panels_slots[panel_id] = slot
                slot.update_state()
                break

    def _connect_device_callback(self, device_id: str):
        if (
            device_id in config.live_devices and config.live_devices[device_id].ready
        ):  # = On device disconnect
            for panel_id, d_id in self.used_panels.items():
                if d_id == device_id:
                    self.used_panels[panel_id] = None
                    self.panels_slots[panel_id] = None
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
        for idx, panel_slot in self.panels_slots.items():
            if panel_slot and panel_slot.contains(note):
                panel_slot.on_pressed(note)
                break

    def handle_release(self, note: int):
        for idx, panel_slot in self.panels_slots.items():
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
            for device_id in config.live_devices.keys():
                self._on_device_connected(device_id)
            return True
        except Exception as e:
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

    def save(self):
        return self.DEVICE_TYPE_NAME, {}

    def load(self, data):
        return True

    @property
    def name(self):
        return f"LaunchpadX ({'Connected' if self.ready else 'Disconnected'})"
