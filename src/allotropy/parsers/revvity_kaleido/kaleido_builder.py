from enum import Enum
import re

from allotropy.parsers.lines_reader import CsvReader, InvertedLinesReader
from allotropy.parsers.utils.values import assert_not_none


class Version(Enum):
    V2 = "2"
    V3 = "3"


def get_version(reader: CsvReader) -> str:
    inv_reader = InvertedLinesReader(reader.lines)
    last_line = assert_not_none(
        inv_reader.pop_data(),
        msg="Unable to get last line of input file.",
    )
    return assert_not_none(
        re.search(r"Exported with Kaleido (\d)", last_line),
        msg="Unable to find Revvity Kaleido version in input file.",
    ).group(1)
