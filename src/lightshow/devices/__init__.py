from typing import TypeGuard

from lightshow.devices.types import DeviceTypeName


def is_device_type(value: str) -> TypeGuard[DeviceTypeName]:
    # This checks if the string exists in the Enum values
    return value in {item.value for item in DeviceTypeName}
