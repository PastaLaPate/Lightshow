from typing import List, Type
import dearpygui.dearpygui as dpg
import threading
import traceback

from lightshow.audio.audio_streams import AudioStreamHandler
from lightshow.devices.device import Device
from lightshow.devices.moving_head.moving_head import MovingHead
from lightshow.gui.utils.message_box import post_ui_message, ui_queue
from lightshow.utils.config import Config, DeviceConfigType, live_devices, resource_path


class UIManager:
    def __init__(
        self,
        audio_listener,
        audio_handler: AudioStreamHandler,
        config: Config,
        audio_devices: List[str],
    ):
        self.listener = audio_listener
        self.audio_handler = audio_handler
        self.config = config
        self.audio_devices = audio_devices
        self.audio_devices.append("-1: Autodetect used device")
        self.is_streaming = False
        self.audio_thread = None

        # --- MODIFIED: Added state for device connection status ---
        self.device_types: List[Type[Device]] = [MovingHead]
        self.selected_device_id = None
        self.connecting_device_id = None
        self.connected_device_id = None

        self._create_context()

    def _show_info(self, title, message, selection_callback):
        """Creates and shows a modal dialog."""
        vpw, vph = dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
        with dpg.window(label=title, modal=True, no_close=True, tag=title) as modal_id:
            dpg.add_text(message)
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Ok",
                    user_data=(modal_id, True),
                    callback=lambda s, a, u: (
                        dpg.delete_item(u[0]),
                        selection_callback(s, a, u),
                    ),
                    width=75,
                )
        dpg.render_dearpygui_frame()
        w, h = dpg.get_item_rect_size(title)
        dpg.set_item_pos(title, [vpw // 2 - w // 2, vph // 2 - h // 2])

    def _process_ui_queue(self):
        """Processes messages from other threads to show UI elements like modals."""
        while not ui_queue.empty():
            title, message, cb = ui_queue.get()
            if title == "FINISH_CONNECTION":
                device_id = message
                self.connected_device_id = device_id
                self.connecting_device_id = None

                # Update UI only if the user is still viewing the device that just connected
                if self.selected_device_id == device_id:
                    dpg.hide_item("connecting_loader")
                    dpg.configure_item(
                        "connect_button", label="Disconnect", enabled=True
                    )
                    dpg.set_value("connection_status_text", "Status: Connected")
            else:
                self._show_info(title, message, cb)

    def _create_context(self):
        dpg.create_context()
        dpg.configure_app(manual_callback_management=True)
        dpg.create_viewport(title="Lightshow GUI", width=1280, height=720)
        with dpg.font_registry():
            # Ensure the asset path is correct for your project structure
            font_path = resource_path("lightshow\\gui\\assets\\OpenSans-Regular.ttf")
            print(font_path)
            self.default_font = dpg.add_font(str(font_path), 20)
            self.large_font = dpg.add_font(str(font_path), 40)

    def _refresh_device_listbox(self):
        device_names = [device_name for device_name in self.config.devices]
        dpg.configure_item("device_listbox", items=device_names)

    def _add_device_callback(self):
        device_type = dpg.get_value("new_device_type_combo")
        if not device_type:
            return

        count = sum(
            1 for dn, d in self.config.devices.items() if d["type"] == device_type
        )
        new_name = f"New {device_type} {count + 1}"

        new_device: DeviceConfigType = {"type": device_type, "props": {}}
        self.config.devices[new_name] = new_device
        self._refresh_device_listbox()

    def _update_device_name_callback(self):
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
        self.selected_device_id = new_name
        self._refresh_device_listbox()

    def _on_device_select(self, sender, app_data):
        selected_device_obj = self.config.devices[app_data]

        if selected_device_obj:
            self.selected_device_id = app_data
            dpg.show_item("device_details_group")
            dpg.hide_item("details_placeholder")

            dpg.set_value("device_name_input", app_data)
            dpg.set_value("device_type_text", f"Type: {selected_device_obj['type']}")

            dpg.delete_item("settings", children_only=True)
            device_type = [
                t
                for t in self.device_types
                if t.DEVICE_TYPE_NAME == selected_device_obj["type"]
            ][0]
            if not device_type:
                return
            for prop_name, prop_type in device_type.EDITABLE_PROPS:
                if prop_type is str:

                    def change(sender, app_data, user_data):
                        self.config.devices[user_data]["props"][prop_name] = app_data

                    dpg.add_input_text(
                        label=prop_name,
                        default_value=self.config.devices[app_data]["props"].get(
                            prop_name, ""
                        ),
                        parent="settings",
                        callback=change,
                        user_data=app_data,
                        tag=prop_name,
                    )

            # --- NEW: Update connection status UI based on selection ---
            dpg.hide_item("connecting_loader")
            dpg.configure_item("connect_button", enabled=True)
            if app_data in live_devices.keys() and live_devices[app_data].ready:
                dpg.configure_item("connect_button", label="Disconnect")
                dpg.set_value("connection_status_text", "Status: Connected")
            elif app_data in live_devices.keys() and not live_devices[app_data].ready:
                dpg.configure_item("connect_button", label="Connecting", enabled=False)
                dpg.show_item("connecting_loader")
                dpg.set_value("connection_status_text", "Status: Connecting...")
            else:
                dpg.configure_item("connect_button", label="Connect")
                dpg.set_value("connection_status_text", "Status: Disconnected")
        else:
            dpg.hide_item("device_details_group")
            dpg.show_item("details_placeholder")

    # --- NEW: Callback for the connect/disconnect button ---
    def _connect_device_callback(self):
        # Handle disconnect
        if (
            self.selected_device_id in live_devices.keys()
            and live_devices[self.selected_device_id or ""].ready
        ):
            live_devices[self.selected_device_id or ""].disconnect()
            del live_devices[self.selected_device_id or ""]
            dpg.configure_item("connect_button", label="Connect")
            dpg.configure_item("delete_button", enabled=True)
            dpg.set_value("connection_status_text", "Status: Disconnected")
            return

        # Handle connect
        if self.selected_device_id and not self.connecting_device_id:
            self.connecting_device_id = self.selected_device_id
            device_type_name = self.config.devices[self.selected_device_id]["type"]
            device_type = [
                t for t in self.device_types if t.DEVICE_TYPE_NAME == device_type_name
            ][0]
            if not device_type:
                return
            live_devices[self.selected_device_id] = device_type()
            for k, v in self.config.devices[self.selected_device_id]["props"].items():
                setattr(live_devices[self.selected_device_id], k, v)
            dpg.configure_item("connect_button", label="Connecting", enabled=False)
            dpg.configure_item("delete_button", enabled=False)
            dpg.show_item("connecting_loader")
            dpg.set_value("connection_status_text", "Status: Connecting...")
            threading.Thread()

            # Simulate network delay in a non-blocking way
            def connection_finished(live_devices, selected_device_id):
                live_devices[selected_device_id].connect(fatal_non_discovery=False)
                dpg.configure_item("delete_button", enabled=False)
                post_ui_message("FINISH_CONNECTION", self.connecting_device_id, None)

            threading.Thread(
                target=connection_finished, args=[live_devices, self.selected_device_id]
            ).start()

    def _delete_device(self):
        if not self.selected_device_id:
            return
        if self.selected_device_id in live_devices:
            live_devices[self.selected_device_id].disconnect()
            del live_devices[self.selected_device_id]
        if self.selected_device_id in self.config.devices:
            del self.config.devices[self.selected_device_id]
        self.selected_device_id = None
        self._refresh_device_listbox()
        dpg.configure_item("device_details_group", show=False)
        dpg.configure_item("details_placeholder", show=True)

    def _create_layout(self):
        with dpg.window(label="Lightshow GUI", tag="main_window"):
            dpg.set_primary_window("main_window", True)
            with dpg.table(
                header_row=False, resizable=True, policy=dpg.mvTable_SizingStretchProp
            ):
                dpg.add_table_column(init_width_or_weight=0.65)
                dpg.add_table_column(init_width_or_weight=0.35)
                with dpg.table_row():
                    with dpg.group():
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
                            dpg.add_plot_axis(
                                dpg.mvXAxis, label="Time", tag="kick_x_axis"
                            )
                            with dpg.plot_axis(
                                dpg.mvYAxis, label="Energy", tag="kick_y_axis"
                            ):
                                self.listener.kick_visualizer.dpg_init("kick_y_axis")

                    with dpg.group():
                        with dpg.child_window(
                            label="Devices",
                            tag="top_pane",
                            height=dpg.get_viewport_client_height() // 2,
                        ):
                            dpg.add_text("Devices", tag="top_pane_header")
                            dpg.bind_item_font("top_pane_header", self.large_font)
                            dpg.add_listbox(
                                items=[d for d in self.config.devices],
                                tag="device_listbox",
                                callback=self._on_device_select,
                                num_items=8,
                            )
                            with dpg.group(horizontal=True):
                                dpg.add_combo(
                                    items=[
                                        device.DEVICE_TYPE_NAME
                                        for device in self.device_types
                                    ],
                                    tag="new_device_type_combo",
                                    default_value=self.device_types[0].DEVICE_TYPE_NAME,
                                    width=150,
                                )
                                dpg.add_button(
                                    label="Add Device",
                                    callback=self._add_device_callback,
                                )

                        with dpg.child_window(label="Device Info", tag="bottom_pane"):
                            dpg.add_text("Device Details", tag="bottom_pane_header")
                            dpg.bind_item_font("bottom_pane_header", self.large_font)
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

                                # --- NEW: Connection Controls ---
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

                                """with dpg.group(tag="wled_settings", show=False):
                                    dpg.add_input_text(
                                        label="URL", default_value="ws://0.0.0.0/ws"
                                    )
                                    dpg.add_slider_int(
                                        label="Brightness",
                                        default_value=128,
                                        max_value=255,
                                    )

                                with dpg.group(tag="moving_head_settings", show=False):
                                    dpg.add_slider_int(label="Pan", max_value=540)
                                    dpg.add_slider_int(label="Tilt", max_value=270)
                                    dpg.add_slider_int(label="Dimmer", max_value=255)
                                    """

        dpg.bind_font(self.default_font)

    def _stream_button_callback(self):
        if not self.is_streaming:
            self._start_stream_callback()
        else:
            self._stop_stream_callback()

    def _start_stream_callback(self):
        try:
            self.audio_handler.reinit_stream(self.config)
            self.listener.clear_state()
            self.audio_thread = threading.Thread(
                target=self.audio_handler.start_stream, daemon=True
            )
            self.audio_thread.start()
            self.is_streaming = True
            dpg.configure_item("stream_button", label="Stop Stream")
            dpg.configure_item("device_combo", enabled=False)
        except Exception:
            post_ui_message(
                "Streaming Error",
                f"Failed to start audio stream:\n\n{traceback.format_exc()}",
                lambda s, a, u: None,
            )
            self.is_streaming = False
            dpg.configure_item("stream_button", label="Start Stream")
            dpg.configure_item("device_combo", enabled=True)

    def _stop_stream_callback(self):
        self.audio_handler.stop_stream()
        self.is_streaming = False
        dpg.configure_item("stream_button", label="Start Stream")
        dpg.configure_item("device_combo", enabled=True)

    def _device_selection_callback(self, sender, app_data):
        self.config.device_index = int(app_data.split(":")[0])

    def run(self):
        dpg.setup_dearpygui()
        self._create_layout()
        dpg.show_viewport()

        while dpg.is_dearpygui_running():
            try:
                jobs = dpg.get_callback_queue()
                dpg.run_callbacks(jobs)
                self._process_ui_queue()

                if self.is_streaming:
                    try:
                        self.listener.kick_visualizer.dpg_update()
                        current_time = self.listener.kick_visualizer.global_index
                        dpg.set_axis_limits(
                            "kick_x_axis", max(0, current_time - 1000), current_time
                        )
                    except Exception as e:
                        self._stop_stream_callback()
                        post_ui_message(
                            "Streaming Error",
                            f"An error occurred during streaming:\n\n{e}\n\n{traceback.format_exc()}",
                            lambda s, a, u: None,
                        )

                dpg.render_dearpygui_frame()
            except Exception as e:
                if self.is_streaming:
                    self._stop_stream_callback()
                post_ui_message(
                    "Unhandled Exception",
                    f"An unexpected error occurred:\n\n{e}\n\n{traceback.format_exc()}",
                    lambda s, a, u: None,
                )

        if self.is_streaming:
            self._stop_stream_callback()
        self.audio_handler.close()
        dpg.destroy_context()
        self.config.save()

    def stop(self):
        if self.is_streaming:
            self._stop_stream_callback()
        self.audio_handler.close()
        dpg.destroy_context()
        self.config.save()
