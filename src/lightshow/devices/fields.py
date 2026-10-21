from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo
from PySide6.QtWidgets import QFileDialog


class WidgetType(StrEnum):
    Field = "field"
    Spinner = "spinner"
    Slider = "slider"  # Custom spinbox  + slider next to it widget
    Checkbox = "checkbox"
    ColorPicker = "colorpicker"
    FileSelector = "fileselector"


class ValidationScheme(StrEnum):
    Email = "email"
    Url = "url"
    IP = "ip"
    IPPort = "ip_port"
    Color = "color"
    Hex = "hex"
    Any = "none"


class FileFilters(StrEnum):
    # Universal
    All = "All Files (*)"

    # Groups & Media
    Images = "Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)"
    Archives = "Archives (*.zip *.tar.gz *.tgz *.rar *.7z)"
    Documents = "Documents (*.pdf *.docx *.doc *.txt *.odt)"

    # Specific Formats
    Png = "PNG Files (*.png)"
    Jpeg = "JPEG Files (*.jpg *.jpeg)"
    Webp = "WebP Files (*.webp)"
    Gif = "GIF Files (*.gif)"

    Json = "JSON Files (*.json)"
    Yaml = "YAML Files (*.yaml *.yml)"
    Csv = "CSV Files (*.csv)"
    Xml = "XML Files (*.xml)"

    Text = "Text Files (*.txt *.log)"
    Markdown = "Markdown Files (*.md)"
    Pdf = "PDF Files (*.pdf)"

    Python = "Python Files (*.py *.pyw)"
    Html = "HTML Files (*.html *.htm)"
    Css = "CSS Files (*.css)"
    JavaScript = "JavaScript Files (*.js *.mjs)"


class FieldExtras(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    widget: WidgetType | None = None  # if None, guess it from python's type
    connected_readonly: bool = False

    placeholder: str | None = None
    step: float | None = None
    validation_scheme: ValidationScheme = ValidationScheme.Any

    # FileSelector specific parameters
    file_selector_title: str | None = None
    file_selector_file_mode: QFileDialog.FileMode = QFileDialog.FileMode.AnyFile
    file_selector_options: QFileDialog.Option | None = None
    file_selector_default_path: str | None = None
    file_selector_filters: list[FileFilters | str] | None = None


def _field(default: Any, extras: FieldExtras, **constraints) -> FieldInfo:
    return Field(
        default, json_schema_extra={"ui": extras.model_dump(mode="json")}, **constraints
    )


def IntField(
    label: str,
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
        FieldExtras(
            label=label, widget=widget, connected_readonly=connected_readonly, step=step
        ),
        ge=min,
        le=max,
    )


def FloatField(
    label: str,
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
        FieldExtras(
            label=label, widget=widget, connected_readonly=connected_readonly, step=step
        ),
        ge=min,
        le=max,
    )


def BoolField(
    label: str,
    default: bool = False,
    widget: Literal[WidgetType.Checkbox] = WidgetType.Checkbox,
    connected_readonly: bool = False,
):
    return _field(
        default,
        FieldExtras(label=label, widget=widget, connected_readonly=connected_readonly),
    )


def StrField(
    label: str,
    default: str = "",
    max_length: int | None = None,
    placeholder: str | None = None,
    validation_scheme: ValidationScheme = ValidationScheme.Any,
    widget: Literal[
        WidgetType.Field, WidgetType.ColorPicker, WidgetType.FileSelector
    ] = WidgetType.Field,
    connected_readonly: bool = False,
):
    return _field(
        default,
        FieldExtras(
            label=label,
            widget=widget,
            connected_readonly=connected_readonly,
            placeholder=placeholder,
            validation_scheme=validation_scheme,
        ),
        max_length=max_length,
    )


def FileSelectorField(
    label: str,
    default: str = "",
    title: str | None = None,
    file_mode: QFileDialog.FileMode = QFileDialog.FileMode.AnyFile,
    options: QFileDialog.Option | None = None,
    default_path: str | None = None,
    filters: list[FileFilters | str] | None = None,
    connected_readonly: bool = False,
):
    return _field(
        default,
        FieldExtras(
            label=label,
            widget=WidgetType.FileSelector,
            connected_readonly=connected_readonly,
            file_selector_title=title,
            file_selector_file_mode=file_mode,
            file_selector_options=options,
            file_selector_default_path=default_path,
            file_selector_filters=filters,
        ),
    )
