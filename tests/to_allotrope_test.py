import os
from pathlib import Path
import re
import warnings

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
    @pytest.mark.skip_ignore_unread_warnings
    def test_positive_cases(
        self, test_file_path: Path, *, overwrite: bool, warn_unread_keys: bool
    ) -> None:
        os.environ["VENDOR"] = self.VENDOR.value
        os.environ.pop("WARN_UNUSED_KEYS", None)
        os.environ.pop("UNREAD_DATA_HANDLED", None)
        if warn_unread_keys or self.VENDOR.unread_data_handled:
            os.environ["WARN_UNUSED_KEYS"] = "1"
        if self.VENDOR.unread_data_handled:
            os.environ["UNREAD_DATA_HANDLED"] = "1"

        # Special case when input files are json, the are placed in an input/ folder and the results are put
        # in a corresponding output/ folder.
        if test_file_path.parts[-2] == "input":
            expected_filepath = Path(
                *test_file_path.parts[:-2], "output", test_file_path.parts[-1]
            ).with_suffix(".json")
        else:
            expected_filepath = test_file_path.with_suffix(".json")

        with warnings.catch_warnings(record=True) as captured_warnings:
            allotrope_dict = from_file(
                str(test_file_path), self.VENDOR, encoding=CHARDET_ENCODING
            )

        # If parser is marked as having unread data handled, error on any unread data warnings.
        for captured_warning in captured_warnings:
            warnings.warn_explicit(
                message=captured_warning.message,
                category=captured_warning.category,
                filename=captured_warning.filename,
                lineno=captured_warning.lineno,
                source=captured_warning.source,
            )
            if isinstance(
                captured_warning.message, UserWarning
            ) and "UNREAD_DATA_HANDLED=True" in str(captured_warning.message):
                msg = "Parser is marked as UNREAD_DATA_HANDLED, but had unread data warnings!"
                raise AssertionError(msg)

        # If expected output does not exist, assume this is a new file and write it.
        overwrite = overwrite or not expected_filepath.exists()
        validate_contents(
            allotrope_dict,
            expected_filepath,
            write_actual_to_expected_on_fail=overwrite,
        )
