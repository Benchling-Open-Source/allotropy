import os
from pathlib import Path
import re

import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents
from allotropy.to_allotrope import allotrope_from_file, allotrope_model_from_file

INVALID_FILE_PATH = "not/a/path"
EXPECTED_ERROR_MESSAGE = f"File not found: {INVALID_FILE_PATH}"


def test_raises_on_invalid_extension() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            "Unsupported file extension 'csv' for parser 'Agilent Gen5', expected one of '['txt']'."
        ),
    ):
        allotrope_from_file(
            "tests/parsers/appbio_absolute_q/testdata/Appbio_AbsoluteQ_example01.csv",
            Vendor.AGILENT_GEN5,
        )


def test_allotrope_from_file_not_found() -> None:
    with pytest.raises(AllotropeConversionError, match=EXPECTED_ERROR_MESSAGE):
        allotrope_from_file(INVALID_FILE_PATH, Vendor.AGILENT_GEN5)


def test_allotrope_model_from_file_not_found() -> None:
    with pytest.raises(AllotropeConversionError, match=EXPECTED_ERROR_MESSAGE):
        allotrope_model_from_file(INVALID_FILE_PATH, Vendor.AGILENT_GEN5)


# A parser can inherit from this test to automatically test all positive test cases of converting from file.
@pytest.mark.long
class ParserTest:
    VENDOR: Vendor

    # test_file_path is automatically populated with all files in testdata folder next to the test file.
    def test_positive_cases(
        self, test_file_path: Path, *, overwrite: bool, warn_unread_keys: bool
    ) -> None:
        if warn_unread_keys:
            os.environ["WARN_UNUSED_KEYS"] = "1"
        expected_filepath = test_file_path.with_suffix(".json")
        allotrope_dict = from_file(
            str(test_file_path), self.VENDOR, encoding=CHARDET_ENCODING
        )
        # If expected output does not exist, assume this is a new file and write it.
        overwrite = overwrite or not expected_filepath.exists()
        validate_contents(
            allotrope_dict,
            expected_filepath,
            write_actual_to_expected_on_fail=overwrite,
        )
