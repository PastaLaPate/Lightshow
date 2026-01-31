from collections import deque
import traceback
from typing import List, Type, Callable, Optional

import numpy as np
# Prefer PyAudioWPatch on Windows where loopback APIs are available, otherwise fall back to standard PyAudio
try:
    import pyaudiowpatch as pyaudio
except Exception:
    try:
        import pyaudio
    except Exception:
        pyaudio = None

from lightshow.audio.audio_types import (
    AAudioCapture,
    AAudioStreamHandler,
    AudioListener,
    Processor,
    AudioListenerType,
)
from lightshow.gui.utils.message_box import post_ui_message
from lightshow.utils.config import Config
from lightshow.utils.logger import Logger


class AudioCapture(AAudioCapture):
    """
    Collects audio data via a PyAudio callback.
    """

    def __init__(
        self,
        processor: Processor,
        stream_handler: AAudioStreamHandler,
        chunk_size=512,
        max_buffer=10,
        channels=1,
        sample_rate=44100,
    ):
        self.stream_handler = stream_handler
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio_buffer = deque(maxlen=max_buffer)
        self.channels = channels  # default is 1
        self.processor = processor
        self.listeners: List[AudioListenerType] = []

    def callback(self, in_data, frame_count, time_info, status):
        """Convert incoming bytes into a numeric array, handling both int16 and float32
        frames. Normalize to float32 in range [-1.0, 1.0] so processors and detectors
        behave consistently across platforms (WASAPI, PulseAudio, PipeWire, etc.)."""
        # Try to infer true channels from the raw buffer length and frame_count.
        # This avoids relying exclusively on device metadata (which may report e.g. 64 channels).
        samples = None
        derived_channels = None

        try:
            raw_i16 = np.frombuffer(in_data, dtype=np.int16)
        except Exception:
            raw_i16 = None
        try:
            raw_f32 = np.frombuffer(in_data, dtype=np.float32)
        except Exception:
            raw_f32 = None

        def channels_from_candidate(arr):
            if arr is None or frame_count == 0:
                return None
            if arr.size % frame_count != 0:
                return None
            return arr.size // frame_count

        ch_i16 = channels_from_candidate(raw_i16)
        ch_f32 = channels_from_candidate(raw_f32)

        # Prefer int16 candidate if it's reasonable (<= 8 channels)
        for cand_arr, cand_ch, dtype in ((raw_i16, ch_i16, "i16"), (raw_f32, ch_f32, "f32")):
            if cand_arr is None or cand_ch is None:
                continue
            if 1 <= cand_ch <= 8:
                derived_channels = cand_ch
                if dtype == "i16":
                    samples = cand_arr.astype(np.float32) / np.iinfo(np.int16).max
                else:
                    samples = cand_arr.astype(np.float32)
                break

        # Fallback: use available raw arrays and clamp device-reported channels
        if samples is None:
            if raw_i16 is not None:
                samples = raw_i16.astype(np.float32) / np.iinfo(np.int16).max
            elif raw_f32 is not None:
                samples = raw_f32.astype(np.float32)
            else:
                samples = np.zeros(self.chunk_size, dtype=np.float32)

            try:
                cand = int(self.channels)
            except Exception:
                cand = 1
            if cand < 1 or cand > 8:
                derived_channels = 1
                #print(
                #    f"Warning: Invalid channel count {self.channels} from device; defaulting to mono."
                #)
            else:
                derived_channels = cand

        # If multi-channel, take first channel per frame; otherwise treat as mono and truncate
        if derived_channels and derived_channels > 1:
            try:
                samples = samples.reshape(-1, derived_channels)[:, 0]
            except Exception:
                samples = samples[: self.chunk_size]
        else:
            samples = samples[: self.chunk_size]

        # Ensure correct buffer length: pad with zeros if too short
        if samples.size < self.chunk_size:
            samples = np.pad(samples, (0, max(0, self.chunk_size - samples.size)), "constant")        
        # Normalize float32 samples: if mostly in [0, 1] range or very small, amplify signal
        # This handles quiet input from default Linux input devices
        max_abs = np.abs(samples).max()
        if 0.001 < max_abs < 0.1:
            # Signal is very quiet, apply moderate amplification
            samples = samples * 5.0
        elif max_abs > 1.0:
            # Clamp to [-1, 1]
            samples = np.clip(samples, -1.0, 1.0)
        treatedData = self.processor.process(samples)

        # Iterate over a copy of listeners to avoid modification during iteration
        for listener in list(self.listeners):
            try:
                if not listener(treatedData):
                    self.listeners.remove(listener)
            except Exception:
                # If a listener raises, remove it to avoid repeated failures
                try:
                    self.listeners.remove(listener)
                except Exception:
                    pass

        self.audio_buffer.append(samples)
        # Use a safe lookup for paContinue in case pyaudio is a fallback placeholder
        paContinue = getattr(pyaudio, "paContinue", 0)
        return (in_data, paContinue)

    def add_listener(self, listener: AudioListenerType) -> Optional[AudioListener]:
        """
        Returns the listener instanced if it was initialy a class.
        """

        if isinstance(listener, type) and issubclass(listener, AudioListener):
            listener = listener(self.stream_handler)
            self.listeners.append(listener)
            return listener
        elif isinstance(listener, AudioListener):
            self.listeners.append(listener)
        elif isinstance(listener, Callable):  # Lambda function
            self.listeners.append(listener)
        else:
            raise ValueError(
                "Listener must be an AudioListener instance, class or a lambda function"
            )
        return None

    def remove_listener(self, listener: Type[AudioListener]):
        if not issubclass(listener, AudioListener):
            raise ValueError("Listener must be an instance of AudioListener")
        self.listeners.remove(listener(self.stream_handler))

    def get_latest_data(self):
        return self.audio_buffer[-1] if self.audio_buffer else None


class AudioStreamHandler(AAudioStreamHandler):
    """
    Sets up the audio device (using WASAPI loopback when available) and manages the stream.
    """

    def __init__(self, processor: Type[Processor], config: Config):
        self.logger = Logger("AudioStreamHandler")
        self.chunk_size = config.chunk_size or 1024
        # Create PyAudio instance if available
        if pyaudio is None:
            self.logger.error("PyAudio is not available. Audio capture will be disabled on this system.")
            self.pyaudio_instance = None
        else:
            self.pyaudio_instance = pyaudio.PyAudio()
        self.processor_class = processor
        self.device_change_listeners: List[Callable[[AudioCapture], None]] = []
        self.pending_listeners = []
        # self.reinit_stream(config)

    def add_device_change_listener(self, listener: Callable[[AudioCapture], None]):
        self.device_change_listeners.append(listener)

    def reinit_stream(self, config: Config):
        """Initializes or re-initializes the stream with a new configuration."""
        self.logger.info("Initializing the stream")
        try:
            if hasattr(self, "stream") and self.stream and self.stream.is_active():
                self.stop_stream()

            self.config = config
            self.stream = None
            self.device_index = None
            self.setup_device()
            self.processor = self.processor_class(self.chunk_size, self.sample_rate)

            # Preserve listeners if AudioCapture already exists
            old_listeners = []
            if hasattr(self, "audio_capture"):
                old_listeners = self.audio_capture.listeners

            self.audio_capture = AudioCapture(
                self.processor,
                self,
                chunk_size=self.chunk_size,
                channels=self.channels,
                sample_rate=self.sample_rate,
            )
            for listener in self.device_change_listeners:
                listener(self.audio_capture)
            self.audio_capture.listeners = old_listeners
            self.logger.info("Adding the listeners")
            for listener in self.pending_listeners:
                self.audio_capture.add_listener(listener)
            self.pending_listeners = []
        except Exception:
            self.logger.error(
                f"Error happened during Initialization: {traceback.format_exc()}"
            )
            post_ui_message("Audio Initialization Error", traceback.format_exc())

    def setup_device(self):
        if not self.pyaudio_instance:
            raise Exception("PyAudio instance not available.")

        # Try WASAPI loopback first (Windows). If not available, fallback to a normal
        # input device (typical on Linux/macOS).
        try:
            wasapi_attr = getattr(pyaudio, "paWASAPI", None)
            if wasapi_attr is not None:
                wasapi_info = self.pyaudio_instance.get_host_api_info_by_type(wasapi_attr)
            else:
                # No WASAPI support in this build
                raise AttributeError("WASAPI not supported")
        except Exception:
            # Fallback path: prefer explicit device_index from config, else use default input
            try:
                if getattr(self.config, "device_index", -1) != -1:
                    default_device = self.pyaudio_instance.get_device_info_by_index(
                        self.config.device_index
                    )
                else:
                    # Typical on Linux: use the default input device
                    default_device = self.pyaudio_instance.get_default_input_device_info()
            except Exception:
                # As a last resort, use device 0
                default_device = self.pyaudio_instance.get_device_info_by_index(0)
        else:
            # WASAPI path (Windows)
            if self.config.device_index == -1:
                default_device = self.pyaudio_instance.get_device_info_by_index(
                    wasapi_info["defaultOutputDevice"]
                )
                if not default_device.get("isLoopbackDevice", False):
                    for loopback in self.pyaudio_instance.get_loopback_device_info_generator():
                        if default_device["name"] in loopback["name"]:
                            default_device = loopback
                            break
                    else:
                        raise Exception(
                            "Default loopback output device not found.\n\n"
                            "Run `python -m pyaudiowpatch` to check available devices.\nExiting..."
                        )
            else:
                default_device = self.pyaudio_instance.get_device_info_by_index(
                    self.config.device_index
                )
                if not default_device.get("isLoopbackDevice", False):
                    raise Exception(
                        f"Device {self.config.device_index} is not a loopback device.\n"
                        "Run `python -m pyaudiowpatch` to check available devices.\nExiting..."
                    )

        # Populate attributes safely, using sensible defaults if keys are missing
        self.device_index = int(default_device.get("index", 0))
        self.sample_rate = int(default_device.get("defaultSampleRate", getattr(self, "sample_rate", 44100)))
        self.channels = int(default_device.get("maxInputChannels", getattr(self, "channels", 1)))
        self.logger.debug(
            f"Using device: {default_device.get('name', '<unknown>')} (index: {self.device_index}) Sample Rate: {self.sample_rate} Hz Channels: {self.channels} Chunk size: {self.chunk_size}"
        )

    def add_listener_on_init(
        self, listener: AudioListenerType
    ) -> Optional[AudioListener]:
        return self.pending_listeners.append(listener)

    def start_stream(self):
        try:
            if not self.pyaudio_instance:
                return
            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                frames_per_buffer=self.chunk_size,
                input=True,
                input_device_index=self.device_index,
                stream_callback=self.audio_capture.callback,
            )
            self.stream.start_stream()
        except Exception:
            self.logger.error(
                f"Failed to start the audio stream: {traceback.format_exc()}"
            )
            post_ui_message("Audio Stream Error", traceback.format_exc())

    def stop_stream(self):
        self.logger.info("Stopping stream")
        if hasattr(self, "stream") and self.stream is not None:
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def close(self):
        """Stops the stream and terminates the PyAudio instance."""
        self.stop_stream()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
