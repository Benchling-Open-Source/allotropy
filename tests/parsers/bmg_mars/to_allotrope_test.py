import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, get_testdata_dir
from tests.to_allotrope_test import ParserTest

TESTDATA = get_testdata_dir(__file__)


class TestParser(ParserTest):
    VENDOR = Vendor.BMG_MARS


def test_to_allotrope_unsupported_kinetic_file() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Unable to parse header data: no key-value pairs found with expected format.",
    ):
        from_file(
            f"{TESTDATA}/errors/file_with_no_delimiter_malformed.csv",
            TestParser.VENDOR,
            encoding=CHARDET_ENCODING,
        )


@pytest.mark.parametrize(
    ("file_name", "expected_well_count"),
    [
        # The column header line ends with a trailing comma, which adds an empty column.
        ("BMG Labtech format.CSV", 96),
        ("PHERAstar output file.CSV", 96),
        # Only 6 of the 32 rows of this 1536 well plate are in the file.
        ("24-10-16 15-09-52 Luminescence 1536.csv", 1536),
        ("16-03-03 13-25-45 472 QC 384 FI.csv", 384),
    ],
)
def test_to_allotrope_plate_well_count(
    file_name: str, expected_well_count: int
) -> None:
    allotrope_dict = from_file(
        f"{TESTDATA}/{file_name}", TestParser.VENDOR, encoding=CHARDET_ENCODING
    )

    plate_documents = allotrope_dict["plate reader aggregate document"][
        "plate reader document"
    ]
    assert plate_documents
    for plate_document in plate_documents:
        assert plate_document["measurement aggregate document"]["plate well count"] == {
            "value": expected_well_count,
            "unit": "#",
        }
