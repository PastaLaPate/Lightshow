from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo


class WidgetType(StrEnum):
    Field = "field"
    Spinner = "spinner"
    Slider = "slider"  # Custom spinbox  + slider next to it widget
    Checkbox = "checkbox"
    ColorPicker = "colorpicker"
    FileSelector = "fileselector"


class FieldExtras(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    widget: WidgetType | None = None  # if None, guess it from python's type
    connected_readonly: bool = False
    step: float | None = None
    placeholder: str | None = None


# TODO: Maybe rename connected_readonly to runtime_immutable or smth like that


def _field(
    default: Any, widget: WidgetType, extras: FieldExtras, **constraints
) -> FieldInfo:
    return Field(
        default, json_schema_extra={"ui": extras.model_dump(mode="json")}, **constraints
    )


def IntField(
    default: int = 0,
    min: int | None = None,
    max: int | None = None,
    step: int | None = 1,
    widget: Literal[WidgetType.Spinner, WidgetType.Slider] = WidgetType.Spinner,
    connected_readonly: bool = False,
):
    if widget is WidgetType.Slider and (min is None or max is None):
        raise ValueError("Can't use a Slider widget without min and max.")
    return _field(
        default,
        widget,
        FieldExtras(widget=widget, connected_readonly=connected_readonly, step=step),
        ge=min,
        le=max,
    )


def FloatField(
    default: float = 0,
    min: float | None = None,
    max: float | None = None,
    step: float | None = 1,
    widget: Literal[WidgetType.Spinner, WidgetType.Slider] = WidgetType.Spinner,
    connected_readonly: bool = False,
):
    if widget is WidgetType.Slider and (min is None or max is None):
        raise ValueError("Can't use a Slider widget without min and max.")
    return _field(
        default,
        widget,
        FieldExtras(widget=widget, connected_readonly=connected_readonly, step=step),
        ge=min,
        le=max,
    )


def BoolField(
    default: bool = False,
    widget: Literal[WidgetType.Checkbox] = WidgetType.Checkbox,
    connected_readonly: bool = False,
):
    return _field(
        default,
        widget,
        FieldExtras(widget=widget, connected_readonly=connected_readonly),
    )


def StrField(
    default: str = "",
    max_length: int | None = None,
    placeholder: str | None = None,
    widget: Literal[
        WidgetType.Field, WidgetType.ColorPicker, WidgetType.FileSelector
    ] = WidgetType.Field,
    connected_readonly: bool = False,
):
    # TODO: Add way to set the str's validation scheme: IP, IP+port, URL, email, color etc. Maybe in the form of another widget type ?
    return _field(
        default,
        widget,
        FieldExtras(
            widget=widget,
            connected_readonly=connected_readonly,
            placeholder=placeholder,
        ),
        max_length=max_length,
    )
