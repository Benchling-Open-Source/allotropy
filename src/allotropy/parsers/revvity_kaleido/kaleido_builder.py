from enum import Enum
import re
from typing import Union

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader, InvertedLinesReader
from allotropy.parsers.revvity_kaleido.kaleido_structure_v2 import DataV2
from allotropy.parsers.revvity_kaleido.kaleido_structure_v3 import DataV3
from allotropy.parsers.utils.values import assert_not_none


class Version(Enum):
    V2 = "2"
    V3 = "3"


def get_version(reader: CsvReader) -> str:
    inv_reader = InvertedLinesReader(reader.lines)
    last_line = assert_not_none(
        inv_reader.pop_data(),
        msg="Unable to find last line of input file.",
    )
    return assert_not_none(
        re.search(r"Exported with Kaleido (\d)", last_line),
        msg="Unable to find Revvity Kaleido version in input file.",
    ).group(1)


def create_data(reader: CsvReader) -> Union[DataV2, DataV3]:
    version = get_version(reader)

    if version == Version.V2.value:
        return DataV2.create(reader)
    elif version == Version.V3.value:
        return DataV3.create(reader)
    else:
        valid_versions = ", ".join([f"v{v.value}.0+" for v in Version])
        error = (
            f"Bad Revvity Kaleido version found. Version supported are {valid_versions}"
        )
        raise AllotropeConversionError(error)
