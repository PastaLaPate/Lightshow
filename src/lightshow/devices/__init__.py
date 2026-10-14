from typing import Final, TypeGuard

from lightshow.devices.device import Device
from lightshow.devices.devices_types import DeviceTypeName
from lightshow.devices.launchpad.launchpad import LaunchpadX
from lightshow.devices.moving_head import MovingHead


def is_device_type(value: str) -> TypeGuard[DeviceTypeName]:
    # This checks if the string exists in the Enum values
    return value in {item.value for item in DeviceTypeName}


DEVICE_TYPES: Final[list[type[Device]]] = [MovingHead, LaunchpadX]
DEVICE_CLASSES: Final[dict[DeviceTypeName, type[Device]]] = {
    d.DEVICE_TYPE_NAME: d for d in DEVICE_TYPES
}
