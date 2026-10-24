from abc import ABC, abstractmethod
from typing import Any, cast, get_args, get_origin

from lightshow.core.debug import who_called_me
from lightshow.core.logger import Logger
from lightshow.core.observable_model import ObservableModel
from lightshow.devices.types import BaseDeviceSettings, DeviceTypeName, PacketData

logger = Logger("BaseDevice")


class NoRuntime(ObservableModel):
    pass


class Device[T: BaseDeviceSettings, R: ObservableModel = NoRuntime](ABC):
    BADGE_COLOR: str

    DEVICE_TYPE_NAME: DeviceTypeName

    CONFIG_SCHEMA: type[T]
    RUNTIME_SCHEMA: type[R]

    def __init_subclass__(cls, *, abstract: bool = False, **kw):
        # Avoids having to redefine CONFIG_SCHEMA and RUNTIME_SCHEMA that are already set by the generics
        super().__init_subclass__(**kw)
        if not abstract and not hasattr(cls, "BADGE_COLOR"):
            raise TypeError(f"{cls.__name__} must define BADGE_COLOR")
        if "RUNTIME_SCHEMA" not in cls.__dict__:
            cls.RUNTIME_SCHEMA = cast(Any, NoRuntime)
        for base in cls.__dict__.get("__orig_bases__", ()):
            origin, args = get_origin(base), get_args(base)
            if not (isinstance(origin, type) and issubclass(origin, Device)):
                continue
            if len(args) == 2 and all(isinstance(a, type) for a in args):
                cls.CONFIG_SCHEMA, cls.RUNTIME_SCHEMA = args

    def __init__(self, config: T):
        super().__init__()
        if not hasattr(self, "CONFIG_SCHEMA"):
            raise TypeError(f"{type(self).__name__} has no CONFIG_SCHEMA")

        self.ready = False
        self.config = config
        self.runtime = self.RUNTIME_SCHEMA()

    def connect(self, fatal_non_discovery=True):
        success = self.scan_for_device()
        if not success and fatal_non_discovery:
            self.ready = False
            raise ConnectionError("No device was found")
        elif not success:
            self.ready = False
            return
        success = self.init_device()
        self.ready = success
        if not success and fatal_non_discovery:
            raise ConnectionRefusedError("The device could not be found")
        return

    @abstractmethod
    def init_device(
        self,
    ) -> bool:  # Returns if the device was successfully initialized
        ...

    @abstractmethod
    def disconnect(self):
        self.ready = False

    @abstractmethod
    def scan_for_device(self) -> bool:  # Returns if a device was found
        ...

    @abstractmethod
    def on_config_changed(self, field: str): ...

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @name.setter
    def name(self, name: str) -> None:
        self.config.name = name

    @id.setter
    def id(self, id: str) -> None:
        logger.warning("Editing a device's id. [%s]", id)
        who_called_me()
        self.config.id = id

    def hsv_to_rgb(self, h: float, s: float, v: float, a: float) -> tuple:
        if s:
            if h == 1.0:
                h = 0.0
            i = int(h * 6.0)
            f = h * 6.0 - i

            w = v * (1.0 - s)
            q = v * (1.0 - s * f)
            t = v * (1.0 - s * (1.0 - f))

            if i == 0:
                return (v, t, w, a)
            if i == 1:
                return (q, v, w, a)
            if i == 2:
                return (w, v, t, a)
            if i == 3:
                return (w, q, v, a)
            if i == 4:
                return (t, w, v, a)
            if i == 5:
                return (v, w, q, a)
        else:
            return (v, v, v, a)
        return (0, 0, 0, a)

    def __str__(self):
        return self.name or "Device"


class OutputDevice[T: BaseDeviceSettings, R: ObservableModel](
    Device[T, R], abstract=True
):
    @abstractmethod
    def on(self, packet: PacketData):
        pass


class InputDevice[T: BaseDeviceSettings, R: ObservableModel](
    Device[T, R], abstract=True
):
    pass
