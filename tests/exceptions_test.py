import pytest

from allotropy.exceptions import AllotropeConversionError


def test_allotrope_conversion_error_no_message() -> None:
    with pytest.raises(ValueError, match="message must not be empty"):
        AllotropeConversionError("")
