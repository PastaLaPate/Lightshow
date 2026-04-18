import threading
from queue import Queue
from typing import Callable, List, Optional, Type

import numpy as np
import soundcard as sc

from lightshow.audio.audio_types import (
    AAudioCapture,
    AAudioStreamHandler,
    AudioListener,
    AudioListenerType,
    Processor,
)
from lightshow.gui.utils.message_box import post_ui_message
from lightshow.utils import global_config
from lightshow.utils.config import Config
from lightshow.utils.logger import Logger

# ---------------------------------------------------------------------------
# LoopbackAudioCapture
# ---------------------------------------------------------------------------


class LoopbackAudioCapture(AAudioCapture):
    """
    Wraps a soundcard loopback microphone and exposes the same interface
    as AudioCapture (queue + listeners).

    soundcard's record() is a blocking call, so capture runs in its own
    thread and pushes chunks into a bounded queue — identical pattern to
    the sounddevice-based AudioCapture.
    """

    def __init__(
        self,
        processor: Processor,
        stream_handler: AAudioStreamHandler,
        loopback_mic,  # soundcard microphone object (loopback=True)
        chunk_size: int = 1024,
        max_buffer: int = 256,
        channels: int = 1,
        sample_rate: int = 44100,
    ):
        # AAudioCapture sets: sample_rate, chunk_size, audio_buffer, channels
        super().__init__(
            processor=processor,
            chunk_size=chunk_size,
            max_buffer=max_buffer,
            channels=channels,
            sample_rate=sample_rate,
        )
        self.logger = Logger("LoopbackAudioCapture")
        self.stream_handler = stream_handler
        self.processor = processor
        self.loopback_mic = loopback_mic
        self.listeners: List[AudioListenerType] = []

        # Bounded queue: excess chunks are dropped to avoid growing backlog
        self.sample_queue: Queue = Queue(maxsize=50)

        self._stop_event = threading.Event()
        self._capture_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # AAudioCapture interface
    # ------------------------------------------------------------------

    def callback(self, in_data, frames, time_info, status):
        """
        Not used directly for soundcard (blocking API), but satisfies the
        abstract interface. Internally we call _enqueue() from the thread.
        """
        self._enqueue(in_data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enqueue(self, raw: np.ndarray) -> None:
        """Normalise a raw frame array and push it onto the queue."""
        # raw shape: (frames, channels) — mix down to mono
        if raw.ndim == 2:
            samples = raw[:, 0].copy()
        else:
            samples = raw.copy()

        # Ensure correct chunk length
        if samples.size < self.chunk_size:
            samples = np.pad(samples, (0, self.chunk_size - samples.size), "constant")
        else:
            samples = samples[: self.chunk_size]

        # Normalise / clamp
        max_abs = float(np.abs(samples).max())
        if 0.001 < max_abs < 0.1:
            samples = samples * 5.0
        elif max_abs > 1.0:
            samples = np.clip(samples, -1.0, 1.0)

        self.audio_buffer.append(samples)

        try:
            self.sample_queue.put(samples, block=True, timeout=0.05)
        except Exception:
            self.logger.debug("Loopback queue full – dropping chunk")

    def _capture_loop(self) -> None:
        """Blocking capture loop – runs in a dedicated thread."""
        self.logger.info("Loopback capture thread started")
        try:
            with self.loopback_mic.recorder(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
            ) as recorder:
                while not self._stop_event.is_set():
                    # record() blocks until chunk_size frames are available
                    data = recorder.record(numframes=self.chunk_size)
                    self._enqueue(data)
        except Exception as e:
            self.logger.error(f"Loopback capture error: {e}")
            import traceback

            traceback.print_exc()
        self.logger.info("Loopback capture thread stopped")

    # ------------------------------------------------------------------
    # Thread control
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._stop_event.clear()
        self._capture_thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="LoopbackCapture"
        )
        self._capture_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

    # ------------------------------------------------------------------
    # Queue processing (call from main / GUI thread, same as AudioCapture)
    # ------------------------------------------------------------------

    def process_queued_samples(self, max_per_frame: int = 25) -> None:
        """
        Drain the queue and call listeners.  Identical contract to the
        sounddevice-based AudioCapture.process_queued_samples().
        """
        processed = 0
        while not self.sample_queue.empty() and processed < max_per_frame:
            try:
                samples = self.sample_queue.get_nowait()
                treated = self.processor.process(samples)

                dead: List[AudioListenerType] = []
                for listener in list(self.listeners):
                    try:
                        keep = listener(treated)
                        if keep is False:
                            dead.append(listener)
                    except Exception as e:
                        self.logger.error(f"Listener error: {e}")
                for d in dead:
                    self.listeners.remove(d)

                processed += 1
            except Exception as e:
                self.logger.error(f"Queue drain error: {e}")
                break

    # ------------------------------------------------------------------
    # Listener management (mirrors AudioCapture)
    # ------------------------------------------------------------------

    def add_listener(self, listener: AudioListenerType) -> Optional[AudioListener]:
        if isinstance(listener, type) and issubclass(listener, AudioListener):
            listener = listener(self.stream_handler)
            self.listeners.append(listener)
            return listener
        elif isinstance(listener, (AudioListener, object)) and callable(listener):
            self.listeners.append(listener)
        else:
            raise ValueError(
                "Listener must be an AudioListener subclass, instance, or callable"
            )
        return None

    def remove_listener(self, listener: AudioListenerType) -> None:
        if listener in self.listeners:
            self.listeners.remove(listener)

    def get_latest_data(self) -> Optional[np.ndarray]:
        return self.audio_buffer[-1] if self.audio_buffer else None


# ---------------------------------------------------------------------------
# LoopbackAudioStreamHandler
# ---------------------------------------------------------------------------


class LoopbackAudioStreamHandler(AAudioStreamHandler):
    """
    Drop-in replacement for AudioStreamHandler that captures speaker
    loopback instead of microphone input.

    Usage
    -----
    handler = LoopbackAudioStreamHandler(MyProcessor, config)
    handler.reinit_stream(config)

    # Optionally pick a specific speaker (defaults to system default):
    handler = LoopbackAudioStreamHandler(MyProcessor, config, speaker_id="Realtek")
    """

    def __init__(self, processor: Type[Processor], config: Config):
        self.logger = Logger("LoopbackAudioStreamHandler")
        self.chunk_size: int = getattr(config, "chunk_size", 1024) or 1024
        self.processor_class = processor

        self.device_change_listeners: List[Callable[[LoopbackAudioCapture], None]] = []
        self.pending_listeners: List[AudioListenerType] = []

        self.audio_capture: Optional[LoopbackAudioCapture] = None
        self._loopback_mic = None  # soundcard mic object

    # ------------------------------------------------------------------
    # AAudioStreamHandler interface
    # ------------------------------------------------------------------

    def add_device_change_listener(
        self, listener: Callable[[LoopbackAudioCapture], None]
    ) -> None:
        self.device_change_listeners.append(listener)

    def reinit_stream(self) -> None:
        # Wait for any existing reinit to finish before starting another
        if (
            hasattr(self, "_reinit_thread")
            and self._reinit_thread
            and self._reinit_thread.is_alive()
        ):
            self.logger.warn("reinit already in progress, skipping")
            return
        self._reinit_thread = threading.Thread(
            target=self._reinit_stream_worker, daemon=True
        )
        self._reinit_thread.start()

    def _reinit_stream_worker(self) -> None:
        self.logger.info("(Re)initialising loopback stream")
        try:
            self.stop_stream()
            self.chunk_size = getattr(global_config, "chunk_size", 1024) or 1024
            self.setup_device()
            self.start_stream()

            if not self.audio_capture:
                raise RuntimeError("audio_capture was not created")

            for listener in self.pending_listeners:
                self.audio_capture.add_listener(listener)
            self.pending_listeners.clear()

        except Exception as e:
            self.logger.error(f"reinit_stream failed: {e}")
            post_ui_message("error", "Audio Error", f"Loopback stream init failed: {e}")

    def setup_device(self) -> None:
        """Resolve the soundcard loopback microphone for the target speaker."""
        try:
            global_config.audio_device.fetch_device()
            self._loopback_mic = global_config.audio_device.device
            self.sample_rate = 44100  # soundcard accepts any common rate
            self.channels = 1  # always capture mono

            self.logger.debug(
                f"Loopback device: '{self._loopback_mic.name}' ({self._loopback_mic.id}) | "
                f"SR={self.sample_rate} | chunk={self.chunk_size}"
            )

        except Exception as e:
            self.logger.error(f"setup_device failed: {e}")
            raise

    def start_stream(self) -> None:
        try:
            processor = self.processor_class(self.chunk_size, self.sample_rate)

            self.audio_capture = LoopbackAudioCapture(
                processor=processor,
                stream_handler=self,
                loopback_mic=self._loopback_mic,
                chunk_size=self.chunk_size,
                channels=self.channels,
                sample_rate=self.sample_rate,
            )

            for listener in self.device_change_listeners:
                listener(self.audio_capture)

            self.audio_capture.start()
            self.logger.info("Loopback stream started")

        except Exception as e:
            self.logger.error(f"start_stream failed: {e}")
            import traceback

            traceback.print_exc()
            post_ui_message(
                "error", "Audio Error", f"Loopback stream start failed: {e}"
            )

    def stop_stream(self) -> None:
        if self.audio_capture:
            self.audio_capture.stop()
            self.pending_listeners = self.audio_capture.listeners.copy()
            self.audio_capture = None
            self.logger.info("Stopping loopback stream")

    def close(self) -> None:
        self.stop_stream()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def add_listener_on_init(self, listener: AudioListenerType) -> None:
        """Register a listener before the stream is started."""
        self.pending_listeners.append(listener)

    @staticmethod
    def list_speakers() -> List[str]:
        """Helper to enumerate available speaker names for speaker_id."""
        return [s.name for s in sc.all_speakers()]
