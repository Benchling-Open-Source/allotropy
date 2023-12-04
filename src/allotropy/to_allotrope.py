from datetime import tzinfo
import io
from pathlib import Path
from typing import Any, Optional

from allotropy.allotrope.allotrope import serialize_allotrope
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parser_factory import get_parser, VendorType


def allotrope_from_io(
    contents: io.IOBase,
    filename: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
) -> dict[str, Any]:
    return serialize_allotrope(
        allotrope_model_from_io(contents, filename, vendor_type, default_timezone)
    )


def allotrope_model_from_io(
    contents: io.IOBase,
    filename: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
) -> Any:
    named_file_contents = NamedFileContents(contents, filename)
    parser = get_parser(vendor_type, default_timezone=default_timezone)
    return parser.to_allotrope(named_file_contents)


def allotrope_from_file(
    filepath: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
) -> dict[str, Any]:
    try:
        with open(filepath, "rb") as f:
            return allotrope_from_io(
                f, Path(filepath).name, vendor_type, default_timezone=default_timezone
            )
    except FileNotFoundError as e:
        msg = f"File not found: {filepath}."
        raise AllotropeConversionError(msg) from e


def allotrope_model_from_file(
    filepath: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
) -> Any:
    with open(filepath, "rb") as f:
        return allotrope_model_from_io(
            f, Path(filepath).name, vendor_type, default_timezone=default_timezone
        )
