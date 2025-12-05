import dearpygui.dearpygui as dpg
import traceback

class BasePanel:
    """Base class for all UI panels with callback support."""
    
    def __init__(self):
        self._callbacks = {}
    
    def register(self, event: str, callback):
        """Register a callback for a named event."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def trigger(self, event: str, *args, **kwargs):
        """Trigger all callbacks registered for an event."""
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception:
                traceback.print_exc()