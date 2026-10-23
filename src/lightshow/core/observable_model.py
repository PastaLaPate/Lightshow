from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, PrivateAttr

Listener = Callable[[str, Any, Any], None]  # (field, old, new)


class ObservableModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    _listeners: list[Listener] = PrivateAttr(default_factory=list)

    def subscribe(self, cb: Listener) -> Callable[[], None]:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    def __setattr__(self, name: str, value: Any) -> None:
        if name not in type(self).model_fields:
            super().__setattr__(name, value)
            return
        old = getattr(self, name)
        super().__setattr__(name, value)
        new = getattr(self, name)
        if old != new:
            for cb in list(self._listeners):
                cb(name, old, new)
