from pathlib import Path

import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents
from allotropy.to_allotrope import allotrope_from_file, allotrope_model_from_file

INVALID_FILE_PATH = "not/a/path"
EXPECTED_ERROR_MESSAGE = f"File not found: {INVALID_FILE_PATH}"


def test_allotrope_from_file_not_found() -> None:
    with pytest.raises(AllotropeConversionError, match=EXPECTED_ERROR_MESSAGE):
        allotrope_from_file(INVALID_FILE_PATH, Vendor.AGILENT_GEN5)


def test_allotrope_model_from_file_not_found() -> None:
    with pytest.raises(AllotropeConversionError, match=EXPECTED_ERROR_MESSAGE):
        allotrope_model_from_file(INVALID_FILE_PATH, Vendor.AGILENT_GEN5)


# A parser can inherit from this test to automatically test all positive test cases of converting from file.
class ParserTest:
    VENDOR: Vendor
    OVERWRITE_ON_FAILURE: bool = False

    # test_file_path is automatically populated with all files in testdata folder next to the test file.
    def test_positive_cases(self, test_file_path: Path) -> None:
        expected_filepath = test_file_path.with_suffix(".json")
        allotrope_dict = from_file(
            str(test_file_path), self.VENDOR, encoding=CHARDET_ENCODING
        )
        # If expected output does not exist, assume this is a new file and write it.
        overwrite = self.OVERWRITE_ON_FAILURE or not expected_filepath.exists()
        validate_contents(
            allotrope_dict,
            expected_filepath,
            write_actual_to_expected_on_fail=overwrite,
        )
