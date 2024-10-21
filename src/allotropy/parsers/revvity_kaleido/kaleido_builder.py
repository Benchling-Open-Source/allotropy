from enum import Enum
import re

from allotropy.exceptions import (
    AllotropeConversionError,
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.lines_reader import CsvReader, InvertedLinesReader
from allotropy.parsers.revvity_kaleido.kaleido_structure import Data
from allotropy.parsers.revvity_kaleido.kaleido_structure_v2 import create_data_v2
from allotropy.parsers.revvity_kaleido.kaleido_structure_v3 import create_data_v3
from allotropy.parsers.utils.values import assert_not_none


class Version(Enum):
    V2 = "2.0"
    V3 = "3.0"
    V3_5 = "3.5"


def get_version(reader: CsvReader) -> str:
    inv_reader = InvertedLinesReader(reader.lines)
    last_line = assert_not_none(
        inv_reader.pop_data(),
        msg="Unable to find last line of input file.",
    )
    return assert_not_none(
        re.search(r"Exported with Kaleido ([\d.]+)", last_line),
        msg="Unable to find Revvity Kaleido version in input file.",
    ).group(1)


def create_data(reader: CsvReader) -> Data:
    version = get_version(reader)

    if version.startswith(Version.V2.value):
        return create_data_v2(version, reader)
    elif version.startswith(Version.V3.value) or version.startswith(Version.V3_5.value):
        return create_data_v3(version, reader)
    else:
        valid_versions = [f"v{v.value}+" for v in Version]
        msg = msg_for_error_on_unrecognized_value(
            "Revvity Kaleido version", version, valid_versions
        )
        raise AllotropeConversionError(msg)
