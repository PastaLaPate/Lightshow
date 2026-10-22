import threading
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from lightshow.audio.streams import LoopbackAudioStreamHandler
from lightshow.core.config import SETTINGS_CATEGORIES, _Settings, global_config
from lightshow.core.logger import Logger
from lightshow.devices.device import Device
from lightshow.devices.registry import DEVICE_TYPES
from lightshow.document.history import global_history
from lightshow.gui.controllers.audio_controller import AudioController
from lightshow.gui.controllers.device_controller import DeviceController
from lightshow.gui.dialogs.about_dialog import AboutDialog
from lightshow.gui.dialogs.settings_dialog import SettingsDialog
from lightshow.gui.input.shortcuts import ShortcutMap, Shortcuts
from lightshow.gui.panels import AudioPanel, DeviceDetailsPanel, DevicesPanel
from lightshow.gui.panels.manual_packets import ManualPacketsSenderPanel
from lightshow.gui.panels.stats import StatsPanel
from lightshow.gui.utils.ui_signals import ui_signals


class UIManager(QMainWindow):
    """Main Qt-based GUI manager for Lightshow."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self, audio_listener, audio_handler: LoopbackAudioStreamHandler):
        super().__init__()
        self.logger = Logger("UIManager")
        self.listener = audio_listener
        self.audio_handler = audio_handler
        self.device_types: list[type[Device]] = DEVICE_TYPES

        # Initialize panels
        self.audio_panel = AudioPanel(audio_listener, audio_handler)
        self.devices_panel = DevicesPanel(self.device_types)
        self.device_details = DeviceDetailsPanel(self.device_types)
        self.manual_packets = ManualPacketsSenderPanel()
        self.stats_panel = StatsPanel()

        self.device_controller = DeviceController()
        self.audio_controller = AudioController(audio_listener, audio_handler)

        # Shortcuts:
        self.shortcut_map = ShortcutMap()

        self.undo_action = QAction("Undo", self)
        self.shortcut_map.apply(self.undo_action, Shortcuts.UNDO)
        self.undo_action.triggered.connect(global_history.undo)
        self.addAction(self.undo_action)

        self.redo_action = QAction("Redo", self)
        self.shortcut_map.apply(self.redo_action, Shortcuts.REDO)
        self.redo_action.triggered.connect(global_history.redo)
        self.addAction(self.redo_action)

        self.about_dialog = AboutDialog(self)
        self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.load(
            SETTINGS_CATEGORIES, saved_values=global_config.settings.as_dict()
        )

        ui_signals.settings.changed.connect(self._apply_settings)
        ui_signals.dialogs.show_error.connect(self._show_error_dialog)
        ui_signals.dialogs.show_info.connect(self._show_info_dialog)

        # Setup UI
        self._setup_ui()

        # Timer for updating visualizations
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_visualizations)
        self.update_timer.start(int(1000 / 60))  # Target X Fps

    @staticmethod
    def init_singleton(audio_listener, audio_handler):
        with UIManager._lock:
            if UIManager._instance is None:
                UIManager._instance = UIManager(audio_listener, audio_handler)

    @staticmethod
    def get() -> UIManager:
        if UIManager._instance is None:
            raise RuntimeError("UIManager not initialized. Call init_singleton first.")
        return UIManager._instance

    def _setup_ui(self):
        self.logger.info("Setting up the UI Layout.")
        """Set up the main UI layout."""
        self.setWindowTitle("Lightshow GUI")
        self.setGeometry(100, 100, 1280, 720)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        full_layout = QVBoxLayout(central_widget)
        full_layout.setContentsMargins(10, 10, 10, 10)

        self._create_menu()

        # Main layout
        main_layout = QHBoxLayout()

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
        splitter.setStretchFactor(0, 650)
        splitter.setStretchFactor(1, 350)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #333;
            }
        """
        )

        main_layout.addWidget(splitter)
        full_layout.addLayout(main_layout, 1)

        stats_layout = QVBoxLayout()
        self.stats_panel.create_qt_ui(stats_layout)
        full_layout.addLayout(stats_layout, 0)

        splitter.setSizes([650, 350])
        right_widget.setSizes([300, 500, 200])

    def _apply_initial_visibility(self) -> None:
        show_spectrum = global_config.settings[_Settings.SHOW_SPECTRUM]
        show_beat = global_config.settings[_Settings.SHOW_BEAT_DETECTION]

        if not show_spectrum:
            QTimer.singleShot(0, lambda: self.audio_panel.spectrumWidget.hide())

        kv = self.audio_panel.kick_visualizer
        if isinstance(kv, QWidget) and not show_beat:
            QTimer.singleShot(0, kv.hide)

    def _create_menu(self):
        if self.menuBar() is None:
            self.setMenuBar(QMenuBar())

        menu_bar = self.menuBar()
        if menu_bar is None:
            return

        edit_menu = menu_bar.addMenu("Edit")
        assert edit_menu is not None
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._show_settings_dialog)
        edit_menu.addAction(settings_action)

        help_menu = menu_bar.addMenu("Help")
        assert help_menu is not None
        about_action = QAction("About Lightshow", self)
        about_action.triggered.connect(self._show_about_dialog)

        help_menu.addAction(about_action)

    def _show_about_dialog(self):
        self.about_dialog.exec()

    def _show_settings_dialog(self):
        self.settings_dialog.exec()

    def _apply_settings(self, settings: dict[str, Any]) -> None:
        global_config.apply(settings)
        global_config.save()

    """

    def _connect_device_callback(self, device_id):
        \"""Handle connect/disconnect button click.\"""
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
        device_type_name = global_config.devices[device_id]["type"]
        device_type = next(
            (t for t in self.device_types if t.DEVICE_TYPE_NAME == device_type_name),
            None,
        )
        if not device_type:
            return

        live_devices[device_id] = device_type()
        for k, v in global_config.devices[device_id]["props"].items():
            setattr(live_devices[device_id], k, v)

        self.device_details.set_connecting(True)
        self.ui_signals.connection_status_changed.emit("Connecting...")

        def connection_finished(live_devices, device_id):
            try:
                live_devices[device_id].connect(fatal_non_discovery=True)
                self.ui_signals.finish_connection.emit(device_id)
            except Exception:  # noqa
                self.device_details.set_connecting(False)
                if self.device_details.connect_button:
                    self.device_details.connect_button.setText("Connect")
                    self.device_details.connect_button.setEnabled(True)
                self.ui_signals.connection_status_changed.emit("Disconnected")
                self.ui_signals.dialogs.show_error.emit(
                    "Connection error",
                    f"Failed to connect to device. Error details: {traceback.format_exc()}",
                )
                if device_id in live_devices:
                    del live_devices[device_id]

        threading.Thread(
            target=connection_finished, args=[live_devices, device_id], daemon=True
        ).start()

    def _on_connection_finished(self, device_id):
        \"""Handle successful connection.\"""
        if self.device_details.selected_device_id != device_id:
            return
        self.device_details.set_connecting(False)
        self.device_details.set_connected(True)
        self.device_details.show_for(device_id)
        self.ui_signals.connection_status_changed.emit("Connected")

    def _on_connection_status_changed(self, status):
        \"""Update connection status display.\"""
        self.device_details.set_status(f"Status: {status}")


    def _send_packet_callback(self, packet_data):
        self.logger.info(
            f"Sending manual packet: {packet_data.packet_type}, {packet_data.packet_status}"
        )
        self.listener.send_packet_to_devices(packet_data, True)
"""

    def _update_visualizations(self):
        """Update visualizations in real-time."""
        # Process queued log messages from background threads
        from lightshow.core.logger import process_log_queue

        process_log_queue()

        # Process queued audio samples (from audio callback thread)
        if (
            self.audio_panel.is_streaming
            and hasattr(self.audio_handler, "audio_capture")
            and self.audio_handler.audio_capture
        ):
            try:
                self.audio_handler.audio_capture.process_queued_samples()
            except Exception as e:  # noqa
                self.logger.error(f"Error processing queued audio: {e}")

        if self.audio_panel.is_streaming and self.audio_panel.kick_visualizer:
            try:
                # Update spike detector visualizer
                self.audio_panel.kick_visualizer.qt_update()
            except Exception as e:  # noqa
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
            # self._stop_stream_callback()
            pass
        self.audio_handler.close()
        global_config.save()

    def closeEvent(self, a0):
        """Handle window close event."""
        self.stop()
        if a0:
            a0.accept()
