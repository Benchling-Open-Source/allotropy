import io
from typing import Any, Optional

import pytest

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.parsers.vendor_parser import VendorParser


class NoneParser(VendorParser):
    def _parse(self, _: io.IOBase, __: str) -> Any:
        pass


@pytest.mark.parametrize(
    "time_str,expected",
    [
        ("Fri, 11 Nov 2011 03:18:09", "2011-11-11T03:18:09+00:00"),
        ("INVALID", None),
        (None, None),
    ],
)
def test_timestamp_parser_default_utc(
    time_str: Optional[str], expected: Optional[str]
) -> None:
    parser = NoneParser(TimestampParser())
    assert parser.parse_timestamp(time_str) == expected


def test_get_date_time() -> None:
    parser = NoneParser(TimestampParser())
    assert (
        parser.get_date_time("Fri, 11 Nov 2011 03:18:09") == "2011-11-11T03:18:09+00:00"
    )

    with pytest.raises(AllotropeConversionError):
        parser.get_date_time("INVALID")
