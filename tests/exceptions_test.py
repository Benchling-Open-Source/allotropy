import pytest

from allotropy.exceptions import AllotropeConversionError


@pytest.mark.parametrize("message", ["", " "])
def test_allotrope_conversion_error_no_message(message: str) -> None:
    with pytest.raises(ValueError, match="message must not be empty"):
        AllotropeConversionError(message)
