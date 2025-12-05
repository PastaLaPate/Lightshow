import dearpygui.dearpygui as dpg
import traceback
import threading

from typing import List, Type
from .base_panel import BasePanel
from lightshow.utils.config import Config
from lightshow.audio.audio_streams import AudioStreamHandler

class AudioPanel(BasePanel):
    """Panel for audio stream control and visualization."""
    
    def __init__(self, listener, audio_handler: AudioStreamHandler, config: Config, audio_devices: List[str]):
        super().__init__()
        self.listener = listener
        self.audio_handler = audio_handler
        self.config = config
        self.audio_devices = audio_devices.copy()
        self.audio_devices.append("-1: Autodetect used device")
        self.is_streaming = False
        self.audio_thread:threading.Thread|None = None
    
    def create(self, default_font):
        """Create the audio panel UI elements."""
        dpg.add_text("Audio")
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Start Stream",
                tag="stream_button",
                callback=self._stream_button_callback,
            )
            dpg.add_combo(
                items=self.audio_devices,
                label="Audio Device",
                tag="device_combo",
                default_value=next(
                    (
                        d
                        for d in self.audio_devices
                        if d.startswith(str(self.config.device_index))
                    ),
                    "",
                ),
                callback=self._device_selection_callback,
            )
        with dpg.plot(
            label="Kick Detector", height=-1, width=-1, tag="main_plot"
        ):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Time", tag="kick_x_axis")
            with dpg.plot_axis(dpg.mvYAxis, label="Energy", tag="kick_y_axis"):
                self.listener.kick_visualizer.dpg_init("kick_y_axis")
                dpg.configure_item("kick_y_axis", auto_fit=True)
    
    def _stream_button_callback(self):
        """Handle stream button clicks."""
        if not self.is_streaming:
            self.trigger("start_stream")
        else:
            self.trigger("stop_stream")
    
    def set_streaming(self, value: bool):
        """Update streaming state and UI."""
        self.is_streaming = value
        dpg.configure_item(
            "stream_button", 
            label="Stop Stream" if value else "Start Stream"
        )
        dpg.configure_item("device_combo", enabled=not value)
    
    def _device_selection_callback(self, sender, app_data):
        """Handle audio device selection."""
        try:
            self.config.device_index = int(app_data.split(":")[0])
            self.trigger("device_changed", app_data)
        except Exception:
            pass