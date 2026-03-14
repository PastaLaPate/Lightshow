from typing import Literal, TypeGuard

DEVICES_STR_TYPES = Literal["LED Moving Head"]
VALID_DEVICE_TYPES: tuple[DEVICES_STR_TYPES, ...] = ("LED Moving Head",)


def is_device_type(value: str) -> TypeGuard[DEVICES_STR_TYPES]:
    return value in VALID_DEVICE_TYPES
