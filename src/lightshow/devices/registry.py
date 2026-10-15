from typing import Final

from lightshow.devices.device import Device
from lightshow.devices.launchpad.launchpad import LaunchpadX
from lightshow.devices.moving_head import MovingHead
from lightshow.devices.types import DeviceTypeName

DEVICE_TYPES: Final[list[type[Device]]] = [MovingHead, LaunchpadX]

DEVICE_CLASSES: Final[dict[DeviceTypeName, type[Device]]] = {
    d.DEVICE_TYPE_NAME: d for d in DEVICE_TYPES
}
