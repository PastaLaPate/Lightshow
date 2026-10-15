from enum import IntEnum, auto


class DeviceStatus(IntEnum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
