import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file, allotrope_model_from_file

INVALID_FILE_PATH = "not/a/path"
EXPECTED_ERROR_MESSAGE = f"File not found: {INVALID_FILE_PATH}"


def test_allotrope_from_file_not_found() -> None:
    with pytest.raises(AllotropeConversionError, match=EXPECTED_ERROR_MESSAGE):
        allotrope_from_file(INVALID_FILE_PATH, Vendor.AGILENT_GEN5)


def test_allotrope_model_from_file_not_found() -> None:
    with pytest.raises(AllotropeConversionError, match=EXPECTED_ERROR_MESSAGE):
        allotrope_model_from_file(INVALID_FILE_PATH, Vendor.AGILENT_GEN5)
