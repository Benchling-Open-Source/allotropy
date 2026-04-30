from datetime import tzinfo
from io import BytesIO
import os
from typing import Any

from allotropy.allotrope.allotrope import serialize_and_validate_allotrope
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parser_factory import discover_vendor, Vendor
from allotropy.parsers.utils.locale_context import set_locale_context
from allotropy.types import IOType

VendorType = Vendor | str


def allotrope_from_io(
    contents: IOType,
    filepath: str,
    vendor_type: VendorType | None = None,
    default_timezone: tzinfo | None = None,
    encoding: str | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    model = allotrope_model_from_io(
        contents, filepath, vendor_type, default_timezone, encoding, locale
    )
    return serialize_and_validate_allotrope(model)


def allotrope_model_from_io(
    contents: IOType,
    filepath: str,
    vendor_type: VendorType | None = None,
    default_timezone: tzinfo | None = None,
    encoding: str | None = None,
    locale: str | None = None,
) -> Any:
    named_file_contents = NamedFileContents(contents, filepath, encoding)

    if vendor_type is None:
        vendor = discover_vendor(named_file_contents)
        named_file_contents.contents.seek(0)
    else:
        try:
            vendor = Vendor(vendor_type)
        except ValueError as e:
            msg = f"Failed to create parser, unregistered vendor: {vendor_type}."
            raise AllotropeConversionError(msg) from e
        if named_file_contents.extension not in vendor.supported_extensions:
            msg = f"Unsupported file extension '{named_file_contents.extension}' for parser '{vendor.display_name}', expected one of '{vendor.supported_extensions}'."
            raise AllotropeConversionError(msg)

    parser = vendor.get_parser(default_timezone=default_timezone)
    if locale:
        with set_locale_context(locale):
            return parser.to_allotrope(named_file_contents)
    else:
        return parser.to_allotrope(named_file_contents)


def allotrope_from_file(
    filepath: str,
    vendor_type: VendorType | None = None,
    default_timezone: tzinfo | None = None,
    encoding: str | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    model = allotrope_model_from_file(
        filepath, vendor_type, default_timezone, encoding, locale
    )
    return serialize_and_validate_allotrope(model)


def allotrope_model_from_file(
    filepath: str,
    vendor_type: VendorType | None = None,
    default_timezone: tzinfo | None = None,
    encoding: str | None = None,
    locale: str | None = None,
) -> Any:
    try:
        if not os.path.isdir(filepath):
            with open(filepath, "rb") as f:
                return allotrope_model_from_io(
                    f,
                    filepath,
                    vendor_type,
                    default_timezone=default_timezone,
                    encoding=encoding,
                    locale=locale,
                )
        else:
            return allotrope_model_from_io(
                BytesIO(b"Parsing Folder"),
                filepath,
                vendor_type,
                default_timezone=default_timezone,
                encoding=encoding,
                locale=locale,
            )
    except FileNotFoundError as e:

        msg = f"File not found: {filepath}."
        raise AllotropeConversionError(msg) from e


def vendor_from_file(filepath: str, encoding: str | None = None) -> Vendor:
    with open(filepath, "rb") as f:
        return vendor_from_io(f, filepath, encoding)


def vendor_from_io(
    contents: IOType, filepath: str, encoding: str | None = None
) -> Vendor:
    named_file_contents = NamedFileContents(contents, filepath, encoding)
    return discover_vendor(named_file_contents)
