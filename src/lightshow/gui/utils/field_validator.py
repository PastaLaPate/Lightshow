import sys
from typing import Annotated, Any

from pydantic_extra_types import Color

if sys.version_info >= (3, 15):
    from typing import TypeForm
else:
    from typing_extensions import TypeForm

from pydantic import (
    AnyUrl,
    EmailStr,
    Field,
    IPvAnyAddress,
    TypeAdapter,
    ValidationError,
)

from lightshow.devices.fields import ValidationScheme

HexStr = Annotated[str, Field(pattern=r"^(?:0x)?[0-9a-fA-F]+$")]
IPPortStr = Annotated[
    str, Field(pattern=r"^(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}$")
]  # Standard IPv4: Port

VALIDATION_MAPPING: dict[ValidationScheme, TypeForm[Any]] = {
    ValidationScheme.Email: EmailStr,
    ValidationScheme.Url: AnyUrl,
    ValidationScheme.IP: IPvAnyAddress,
    ValidationScheme.IPPort: IPPortStr,
    ValidationScheme.Color: Color,
    ValidationScheme.Hex: HexStr,
    ValidationScheme.Any: Any,
}


def validate_value(scheme: ValidationScheme, value: str) -> bool:
    target_type = VALIDATION_MAPPING.get(scheme)
    if not target_type:
        raise ValueError(f"Scheme {scheme} isnt supported")

    adapter = TypeAdapter(target_type)
    try:
        adapter.validate_python(value)
        return True
    except ValidationError:
        return False
