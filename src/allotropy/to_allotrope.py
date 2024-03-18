from datetime import tzinfo
from pathlib import Path
from typing import Any, Optional, Union

from allotropy.allotrope.allotrope import serialize_and_validate_allotrope
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parser_factory import get_parser, Vendor
from allotropy.types import IOType

VendorType = Union[Vendor, str]


def allotrope_from_io(
    contents: IOType,
    filename: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
    encoding: Optional[str] = None,
) -> dict[str, Any]:
    model = allotrope_model_from_io(
        contents, filename, vendor_type, default_timezone, encoding
    )
    return serialize_and_validate_allotrope(model)


def allotrope_model_from_io(
    contents: IOType,
    filename: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
    encoding: Optional[str] = None,
) -> Any:
    try:
        vendor = Vendor(vendor_type)
    except ValueError as e:
        error = f"Failed to create parser, unregistered vendor: {vendor_type}."
        raise AllotropeConversionError(error) from e
    named_file_contents = NamedFileContents(contents, filename, encoding)
    parser = get_parser(vendor, default_timezone=default_timezone)
    return parser.to_allotrope(named_file_contents)


def allotrope_from_file(
    filepath: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
    encoding: Optional[str] = None,
) -> dict[str, Any]:
    model = allotrope_model_from_file(filepath, vendor_type, default_timezone, encoding)
    return serialize_and_validate_allotrope(model)


def allotrope_model_from_file(
    filepath: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
    encoding: Optional[str] = None,
) -> Any:
    try:
        with open(filepath, "rb") as f:
            return allotrope_model_from_io(
                f,
                Path(filepath).name,
                vendor_type,
                default_timezone=default_timezone,
                encoding=encoding,
            )
    except FileNotFoundError as e:
        msg = f"File not found: {filepath}."
        raise AllotropeConversionError(msg) from e
