from typing import Any, Final

from lightshow.core.observable_model import ObservableModel
from lightshow.devices.device import Device
from lightshow.devices.launchpadx import LaunchpadX
from lightshow.devices.moving_head import MovingHead
from lightshow.devices.types import BaseDeviceSettings, DeviceTypeName

DEVICE_TYPES: Final[list[type[Device[Any, Any]]]] = [
    MovingHead,
    LaunchpadX,
]

DEVICE_CLASSES: Final[
    dict[DeviceTypeName, type[Device[BaseDeviceSettings, ObservableModel]]]
] = {d.DEVICE_TYPE_NAME: d for d in DEVICE_TYPES}
