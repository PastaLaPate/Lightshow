import dearpygui.dearpygui as dpg
from typing import List, Type
from .base_panel import BasePanel
from lightshow.utils.config import Config, DeviceConfigType, live_devices, resource_path
from lightshow.devices.device import Device

class DeviceDetailsPanel(BasePanel):
    """Panel for displaying and managing device configuration details."""
    
    def __init__(self, config: Config, device_types: List[Type[Device]]):
        super().__init__()
        self.config = config
        self.device_types = device_types
        self.selected_device_id = None
    
    def create(self, large_font):
        """Create the device details panel UI elements."""
        with dpg.child_window(label="Device Info", tag="bottom_pane"):
            dpg.add_text("Device Details", tag="bottom_pane_header")
            dpg.bind_item_font("bottom_pane_header", large_font)
            dpg.add_text(
                "Select a device to see its details.",
                tag="details_placeholder",
            )
            
            with dpg.group(tag="device_details_group", show=False):
                dpg.add_input_text(
                    label="Device Name",
                    tag="device_name_input",
                    callback=self._update_device_name_callback,
                    on_enter=True,
                )
                dpg.add_text("", tag="device_type_text")
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Connect",
                        tag="connect_button",
                        callback=self._connect_device_callback,
                    )
                    dpg.add_loading_indicator(
                        tag="connecting_loader",
                        show=False,
                        style=1,
                        radius=2,
                    )
                    dpg.add_button(
                        label="Delete",
                        tag="delete_button",
                        callback=self._delete_device,
                    )
                dpg.add_text(
                    "Status: Disconnected", tag="connection_status_text"
                )
                dpg.add_separator(tag="settings_first_sep")
                with dpg.group(tag="settings"):
                    pass
                dpg.add_separator(tag="settings_sep")
    
    def show_for(self, device_id):
        """Display details for a specific device."""
        if not device_id or device_id not in self.config.devices:
            dpg.hide_item("device_details_group")
            dpg.show_item("details_placeholder")
            self.selected_device_id = None
            return
        
        selected_device_obj = self.config.devices[device_id]
        self.selected_device_id = device_id
        dpg.show_item("device_details_group")
        dpg.hide_item("details_placeholder")
        
        dpg.set_value("device_name_input", device_id)
        dpg.set_value("device_type_text", f"Type: {selected_device_obj['type']}")
        
        # Populate device-specific settings
        dpg.delete_item("settings", children_only=True)
        device_type = next(
            (t for t in self.device_types 
             if t.DEVICE_TYPE_NAME == selected_device_obj["type"]),
            None
        )
        if device_type:
            for prop_name, prop_type in device_type.EDITABLE_PROPS:
                if prop_type is str:
                    def change(sender, app_data):
                        self.config.devices[device_id]["props"][prop_name] = app_data
                    
                    dpg.add_input_text(
                        label=prop_name,
                        default_value=self.config.devices[device_id]["props"].get(
                            prop_name, ""
                        ),
                        parent="settings",
                        callback=change,
                        tag=prop_name,
                    )
        
        # Update connection status UI
        dpg.hide_item("connecting_loader")
        dpg.configure_item("connect_button", enabled=True)
        if device_id in live_devices and live_devices[device_id].ready:
            dpg.configure_item("connect_button", label="Disconnect")
            dpg.set_value("connection_status_text", "Status: Connected")
        elif device_id in live_devices and not live_devices[device_id].ready:
            dpg.configure_item("connect_button", label="Connecting", enabled=False)
            dpg.show_item("connecting_loader")
            dpg.set_value("connection_status_text", "Status: Connecting...")
        else:
            dpg.configure_item("connect_button", label="Connect")
            dpg.set_value("connection_status_text", "Status: Disconnected")
    
    def _update_device_name_callback(self, sender, app_data):
        """Handle device name changes."""
        if not self.selected_device_id:
            return
        
        new_name = dpg.get_value("device_name_input")
        if not new_name:
            dpg.set_value("device_name_input", self.selected_device_id)
            return
        if new_name == self.selected_device_id:
            return
        
        self.config.devices[new_name] = self.config.devices[self.selected_device_id]
        del self.config.devices[self.selected_device_id]
        old_id = self.selected_device_id
        self.selected_device_id = new_name
        self.trigger("device_renamed", old_id, new_name)
    
    def _connect_device_callback(self):
        """Handle connect button click."""
        self.trigger("connect_clicked", self.selected_device_id)
    
    def _delete_device(self):
        """Handle delete button click."""
        self.trigger("delete_clicked", self.selected_device_id)