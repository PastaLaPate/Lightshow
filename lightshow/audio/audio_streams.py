import sounddevice as sd
import numpy as np
from collections import deque
from typing import List, Type, Callable, Optional
from queue import Queue

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
    Collects audio data via a sounddevice stream callback.
    Uses a queue to pass raw samples to be processed on the main thread.
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
        self.channels = channels
        self.processor = processor
        self.listeners: List[AudioListenerType] = []
        # Queue for passing raw samples from audio callback to main thread
        # Smaller queue prevents 2+ second backlog. Excess audio dropped.
        self.sample_queue = Queue(maxsize=5)

    def callback(self, indata, frames, time_info, status):
        """Minimal callback - just extract and queue audio, don't process."""
        try:
            if status:
                print(f"Audio callback status: {status}")

            # indata is array with shape (frames, channels), always extract first channel
            samples = indata[:, 0].copy()
            
            # Ensure correct buffer length
            if samples.size < self.chunk_size:
                samples = np.pad(samples, (0, max(0, self.chunk_size - samples.size)), "constant")
            else:
                samples = samples[:self.chunk_size].copy()

            # Normalize if needed
            max_abs = np.abs(samples).max()
            if 0.001 < max_abs < 0.1:
                # Signal is very quiet, apply moderate amplification
                samples = samples * 5.0
            elif max_abs > 1.0:
                # Clamp to [-1, 1]
                samples = np.clip(samples, -1.0, 1.0)

            self.audio_buffer.append(samples)
            
            # Queue samples for processing on main thread (don't block)
            try:
                self.sample_queue.put_nowait(samples)
            except:
                # Queue full, drop sample
                pass
                
        except Exception as e:
            import traceback
            print(f"Critical error in audio callback: {e}")
            traceback.print_exc()

    def process_queued_samples(self, max_per_frame=15):
        """
        Process queued audio samples - call this from main thread.
        Limits processing to max_per_frame FFTs to keep up with audio rate.
        At 44.1kHz with 1024-sample chunks, audio arrives ~43 times/sec.
        With GUI at 30fps, need ~1.4 per frame minimum. 15 keeps us ahead.
        """
        processed_count = 0
        while not self.sample_queue.empty() and processed_count < max_per_frame:
            try:
                samples = self.sample_queue.get_nowait()
                # Process samples
                treatedData = self.processor.process(samples)
                
                # Call listeners
                for listener in list(self.listeners):
                    try:
                        listener(treatedData)
                    except Exception as e:
                        import traceback
                        print(f"Error in listener: {e}")
                        traceback.print_exc()
                processed_count += 1
            except Exception as e:
                print(f"Error processing queued sample: {e}")
                break

    def add_listener(self, listener: AudioListenerType) -> Optional[AudioListener]:
        """
        Returns the listener instanced if it was initially a class.
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
    Sets up the audio device using sounddevice and manages the stream.
    """

    def __init__(self, processor: Type[Processor], config: Config):
        self.logger = Logger("AudioStreamHandler")
        self.chunk_size = config.chunk_size or 1024
        self.processor_class = processor
        self.device_change_listeners: List[Callable[[AudioCapture], None]] = []
        self.pending_listeners = []
        self.stream = None
        self.audio_capture = None

    def add_device_change_listener(self, listener: Callable[[AudioCapture], None]):
        self.device_change_listeners.append(listener)

    def reinit_stream(self, config: Config):
        """Initializes or re-initializes the stream with a new configuration."""
        self.logger.info("Initializing the stream")
        try:
            if self.stream and self.stream.active:
                self.stream.stop()
                self.stream.close()

            self.config = config
            self.stream = None
            self.setup_device()
            self.start_stream()
            
            # Add any pending listeners
            for listener in self.pending_listeners:
                self.audio_capture.add_listener(listener)
            self.pending_listeners = []
            
        except Exception as e:
            self.logger.error(f"Error initializing stream: {e}")
            post_ui_message("error", "Audio Error", f"Failed to initialize audio stream: {e}")

    def setup_device(self):
        """Setup audio device using sounddevice."""
        try:
            # Get default input device
            device_info = sd.query_devices(kind='input')
            self.device_index = sd.default.device[0]
            self.sample_rate = int(device_info['default_samplerate'])
            self.channels = min(device_info['max_input_channels'], 1)  # Use mono
            
            self.logger.debug(
                f"Using device: {device_info['name']} (index: {self.device_index}) "
                f"Sample Rate: {self.sample_rate} Hz Channels: {self.channels} "
                f"Chunk size: {self.chunk_size}"
            )
        except Exception as e:
            self.logger.error(f"Error setting up device: {e}")
            self.device_index = sd.default.device[0]
            self.sample_rate = 44100
            self.channels = 1

    def add_listener_on_init(self, listener: AudioListenerType) -> Optional[AudioListener]:
        self.pending_listeners.append(listener)
        return None

    def start_stream(self):
        """Start the audio stream using sounddevice."""
        try:
            self.logger.debug("Creating processor...")
            # Create processor instance
            processor = self.processor_class(self.chunk_size, self.sample_rate)
            
            self.logger.debug("Creating audio capture...")
            # Create audio capture
            self.audio_capture = AudioCapture(
                processor=processor,
                stream_handler=self,
                chunk_size=self.chunk_size,
                channels=self.channels,
                sample_rate=self.sample_rate,
            )
            
            self.logger.debug("Notifying device change listeners...")
            # Notify device change listeners
            for listener in self.device_change_listeners:
                listener(self.audio_capture)
            
            self.logger.debug("Creating sounddevice InputStream...")
            # Create and start sounddevice stream
            self.stream = sd.InputStream(
                device=self.device_index,
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                callback=self.audio_capture.callback,
                dtype='float32',
            )
            self.logger.debug("Starting audio stream...")
            self.stream.start()
            self.logger.info("Audio stream started")
            
        except Exception as e:
            self.logger.error(f"Error starting stream: {e}")
            import traceback
            traceback.print_exc()
            post_ui_message("error", "Audio Error", f"Failed to start audio stream: {e}")

    def stop_stream(self):
        """Stop the audio stream."""
        self.logger.info("Stopping stream")
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            except Exception as e:
                self.logger.error(f"Error stopping stream: {e}")

    def close(self):
        """Stops the stream and closes audio resources."""
        self.stop_stream()
