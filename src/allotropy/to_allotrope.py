from datetime import tzinfo
from pathlib import Path
from typing import Any, Optional

from allotropy.allotrope.allotrope import serialize_allotrope
from allotropy.parser_factory import PARSER_FACTORY, VendorType
from allotropy.types import ContentsType


def allotrope_from_io(
    contents: ContentsType,
    filename: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
) -> dict[str, Any]:
    return serialize_allotrope(
        allotrope_model_from_io(contents, filename, vendor_type, default_timezone)
    )


def allotrope_model_from_io(
    contents: ContentsType,
    filename: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
) -> Any:
    parser = PARSER_FACTORY.create(vendor_type, default_timezone=default_timezone)
    return parser.to_allotrope(contents, filename)


def allotrope_from_file(
    filepath: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
) -> dict[str, Any]:
    with open(filepath, "rb") as f:
        return allotrope_from_io(
            f, Path(filepath).name, vendor_type, default_timezone=default_timezone
        )


def allotrope_model_from_file(
    filepath: str,
    vendor_type: VendorType,
    default_timezone: Optional[tzinfo] = None,
) -> Any:
    with open(filepath, "rb") as f:
        return allotrope_model_from_io(
            f, Path(filepath).name, vendor_type, default_timezone=default_timezone
        )
