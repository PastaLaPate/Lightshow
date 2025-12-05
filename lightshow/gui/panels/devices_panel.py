import dearpygui.dearpygui as dpg
from typing import List, Type
from .base_panel import BasePanel
from lightshow.utils.config import Config, DeviceConfigType
from lightshow.devices.device import Device


class DevicesPanel(BasePanel):
    """Panel for managing device list and additions."""
    
    def __init__(self, config: Config, device_types: List[Type[Device]]):
        super().__init__()
        self.config = config
        self.device_types = device_types
    
    def refresh_list(self):
        """Refresh the device listbox with current devices."""
        device_names = list(self.config.devices.keys())
        if dpg.does_item_exist("device_listbox"):
            dpg.configure_item("device_listbox", items=device_names)
    
    def create(self, large_font):
        """Create the devices panel UI elements."""
        with dpg.child_window(
            label="Devices",
            tag="top_pane",
            height=dpg.get_viewport_client_height() // 2,
        ):
            dpg.add_text("Devices", tag="top_pane_header")
            dpg.bind_item_font("top_pane_header", large_font)
            dpg.add_listbox(
                items=[d for d in self.config.devices],
                tag="device_listbox",
                callback=self._on_device_select,
                num_items=8,
            )
            with dpg.group(horizontal=True):
                dpg.add_combo(
                    items=[device.DEVICE_TYPE_NAME for device in self.device_types],
                    tag="new_device_type_combo",
                    default_value=self.device_types[0].DEVICE_TYPE_NAME,
                    width=150,
                )
                dpg.add_button(
                    label="Add Device",
                    callback=self._add_device_callback,
                )
    
    def _add_device_callback(self):
        """Handle adding a new device."""
        device_type = dpg.get_value("new_device_type_combo")
        if not device_type:
            return
        
        count = sum(
            1 for dn, d in self.config.devices.items() if d["type"] == device_type
        )
        new_name = f"New {device_type} {count + 1}"
        new_device: DeviceConfigType = {"type": device_type, "props": {}}
        self.config.devices[new_name] = new_device
        self.refresh_list()
        self.trigger("device_added", new_name)
    
    def _on_device_select(self, sender, app_data):
        """Handle device selection from listbox."""
        self.trigger("device_selected", app_data)