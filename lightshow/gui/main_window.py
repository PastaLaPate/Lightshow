import threading
import traceback
from typing import List, Type

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from lightshow.audio.audio_streams import AudioStreamHandler
from lightshow.devices.device import Device
from lightshow.devices.moving_head.moving_head import MovingHead
from lightshow.gui.panels import AudioPanel, DeviceDetailsPanel, DevicesPanel
from lightshow.gui.panels.manual_packets import ManualPacketsSenderPanel
from lightshow.utils.config import Config, live_devices
from lightshow.utils.logger import Logger


class UISignals(QObject):
    """Signals for thread-safe communication with UI."""

    finish_connection = pyqtSignal(str)
    show_error = pyqtSignal(str, str)
    show_info = pyqtSignal(str, str)
    connection_status_changed = pyqtSignal(str)


class UIManager(QMainWindow):
    """Main Qt-based GUI manager for Lightshow."""

    def __init__(
        self,
        audio_listener,
        audio_handler: AudioStreamHandler,
        config: Config,
        audio_devices: List[str],
    ):
        super().__init__()
        self.logger = Logger("UIManager")
        self.listener = audio_listener
        self.audio_handler = audio_handler
        self.config = config
        self.device_types: List[Type[Device]] = [MovingHead]
        self.ui_signals = UISignals()

        # Initialize panels
        self.audio_panel = AudioPanel(
            audio_listener, audio_handler, config, audio_devices
        )
        self.devices_panel = DevicesPanel(config, self.device_types)
        self.device_details = DeviceDetailsPanel(config, self.device_types)
        self.manual_packets = ManualPacketsSenderPanel()

        # Register internal handlers
        self.audio_panel.register("start_stream", self._start_stream_callback)
        self.audio_panel.register("stop_stream", self._stop_stream_callback)

        self.devices_panel.register("device_selected", self._on_device_select)
        self.devices_panel.register("device_added", lambda name: None)

        self.device_details.register("connect_clicked", self._connect_device_callback)
        self.device_details.register("delete_clicked", self._delete_device)
        self.device_details.register("device_renamed", self._on_device_renamed)

        self.manual_packets.register("send_manual_packet", self._send_packet_callback)

        # Connect signals
        self.ui_signals.finish_connection.connect(self._on_connection_finished)
        self.ui_signals.show_error.connect(self._show_error_dialog)
        self.ui_signals.show_info.connect(self._show_info_dialog)
        self.ui_signals.connection_status_changed.connect(
            self._on_connection_status_changed
        )

        # Setup UI
        self._setup_ui()

        # Timer for updating visualizations
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_visualizations)
        self.update_timer.start(int(1000 / 30))  # Target X Fps

    def register(self, panel: str, event: str, callback):
        """Public API to register custom callbacks on panels."""
        mapping = {
            "audio": self.audio_panel,
            "devices": self.devices_panel,
            "details": self.device_details,
        }
        target = mapping.get(panel)
        if not target:
            raise ValueError(
                f"Unknown panel: {panel}. Must be one of {list(mapping.keys())}"
            )
        target.register(event, callback)

    def _setup_ui(self):
        self.logger.info("Setting up the UI Layout.")
        """Set up the main UI layout."""
        self.setWindowTitle("Lightshow GUI")
        self.setGeometry(100, 100, 1280, 720)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Left side: Audio panel (65%)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.audio_panel.create_qt_ui(left_layout)

        # Right side: Devices panel (35%)
        devices_list_w = QWidget()
        devices_list = QVBoxLayout(devices_list_w)
        self.devices_panel.create_qt_ui(devices_list)

        device_details_w = QWidget()
        device_details = QVBoxLayout(device_details_w)
        self.device_details.create_qt_ui(device_details)

        manual_packets_w = QWidget()
        manual_packets = QVBoxLayout(manual_packets_w)
        self.manual_packets.create_qt_ui(manual_packets)

        right_widget = QSplitter(Qt.Orientation.Vertical)
        right_widget.addWidget(devices_list_w)
        right_widget.addWidget(device_details_w)
        right_widget.addWidget(manual_packets_w)
        right_widget.setStretchFactor(0, 30)
        right_widget.setStretchFactor(1, 50)
        right_widget.setStretchFactor(2, 20)
        right_widget.setHandleWidth(1)
        right_widget.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #333;
            }                       
        """
        )

        # Add splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 65)
        splitter.setStretchFactor(1, 35)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #333;
            }                       
        """
        )

        main_layout.addWidget(splitter)
        splitter.setSizes([65, 35])
        right_widget.setSizes([30, 50, 20])

    def _on_device_select(self, device_name):
        """Handle device selection."""
        self.device_details.show_for(device_name)

    def _on_device_renamed(self, old_id, new_id):
        """Handle device rename."""
        self.devices_panel.refresh_list()
        self.device_details.show_for(new_id)

    def _connect_device_callback(self, device_id):
        """Handle connect/disconnect button click."""
        if not device_id:
            return
        self.logger.info(f"Connecting to device {device_id}")

        # Handle disconnect
        if device_id in live_devices and live_devices[device_id].ready:
            live_devices[device_id].disconnect()
            del live_devices[device_id]
            self.device_details.set_connected(False)
            self.ui_signals.connection_status_changed.emit("Disconnected")
            return

        # Handle connect
        device_type_name = self.config.devices[device_id]["type"]
        device_type = next(
            (t for t in self.device_types if t.DEVICE_TYPE_NAME == device_type_name),
            None,
        )
        if not device_type:
            return

        live_devices[device_id] = device_type()
        for k, v in self.config.devices[device_id]["props"].items():
            setattr(live_devices[device_id], k, v)

        self.device_details.set_connecting(True)
        self.ui_signals.connection_status_changed.emit("Connecting...")

        def connection_finished(live_devices, device_id):
            try:
                live_devices[device_id].connect(fatal_non_discovery=True)
                self.ui_signals.finish_connection.emit(device_id)
            except Exception as e:
                self.device_details.set_connecting(False)
                if self.device_details.connect_button:
                    self.device_details.connect_button.setText("Connect")
                    self.device_details.connect_button.setEnabled(True)
                self.ui_signals.connection_status_changed.emit("Disconnected")
                self.ui_signals.show_error.emit("Connection error", repr(e))
                if device_id in live_devices:
                    del live_devices[device_id]

        threading.Thread(
            target=connection_finished, args=[live_devices, device_id], daemon=True
        ).start()

    def _on_connection_finished(self, device_id):
        """Handle successful connection."""
        if self.device_details.selected_device_id != device_id:
            return
        self.device_details.set_connecting(False)
        self.device_details.set_connected(True)
        self.device_details.show_for(device_id)
        self.ui_signals.connection_status_changed.emit("Connected")

    def _on_connection_status_changed(self, status):
        """Update connection status display."""
        self.device_details.set_status(f"Status: {status}")

    def _delete_device(self, device_id):
        """Handle device deletion."""
        if not device_id:
            return
        if device_id in live_devices:
            live_devices[device_id].disconnect()
            del live_devices[device_id]
        if device_id in self.config.devices:
            del self.config.devices[device_id]
        self.device_details.selected_device_id = None
        self.devices_panel.refresh_list()
        self.device_details.clear()

    def _start_stream_callback(self):
        """Start audio stream."""
        try:
            self.audio_handler.reinit_stream(self.config)
            self.listener.clear_state()
            self.audio_panel.audio_thread = threading.Thread(
                target=self.audio_handler.start_stream, daemon=True
            )
            self.audio_panel.audio_thread.start()
            self.audio_panel.set_streaming(True)
        except Exception:
            self.ui_signals.show_error.emit(
                "Streaming Error",
                f"Failed to start audio stream:\n\n{traceback.format_exc()}",
            )
            self.audio_panel.set_streaming(False)

    def _stop_stream_callback(self):
        """Stop audio stream."""
        self.audio_handler.stop_stream()
        self.audio_panel.set_streaming(False)

    def _send_packet_callback(self, packet_data):
        self.logger.info(
            f"Sending manual packet: {packet_data.packet_type}, {packet_data.packet_status}"
        )
        self.listener.send_packet_to_devices(packet_data)

    def _update_visualizations(self):
        """Update visualizations in real-time."""
        # Process queued log messages from background threads
        from lightshow.utils.logger import LoggerCore

        LoggerCore().process_log_queue()

        if self.audio_panel.is_streaming and self.audio_panel.visualizer:
            try:
                # Update spike detector visualizer
                self.audio_panel.visualizer.qt_update()
            except Exception as e:
                self.logger.error(f"Visualization update error: {e}")

    def _show_error_dialog(self, title, message):
        """Show error dialog."""
        QMessageBox.critical(self, title, message)

    def _show_info_dialog(self, title, message):
        """Show info dialog."""
        QMessageBox.information(self, title, message)

    def stop(self):
        """Gracefully stop the application and clean up resources."""
        self.update_timer.stop()
        if self.audio_panel.is_streaming:
            self._stop_stream_callback()
        self.audio_handler.close()
        self.config.save()

    def closeEvent(self, a0):
        """Handle window close event."""
        self.stop()
        if a0:
            a0.accept()
