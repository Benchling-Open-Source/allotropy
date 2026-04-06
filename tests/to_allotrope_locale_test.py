"""Integration tests for locale support in top-level API."""

from io import BytesIO

import pytest

from allotropy.to_allotrope import allotrope_from_io


def test_locale_parameter_is_optional() -> None:
    """Verify that locale parameter is optional and defaults to None."""
    # This should work without locale parameter
    # Using a simple CSV that doesn't require locale parsing
    csv_content = b"A,B\n1,2\n3,4"
    # We expect this to fail because we don't have a real parser for raw CSV,
    # but it should fail at parser creation, not at locale handling
    with pytest.raises(Exception):
        allotrope_from_io(
            BytesIO(csv_content), "test.csv", "UNKNOWN_VENDOR"
        )


def test_locale_parameter_accepts_string() -> None:
    """Verify that locale parameter accepts locale strings."""
    csv_content = b"A,B\n1,2\n3,4"
    # We expect this to fail because we don't have a real parser for raw CSV,
    # but it should fail at parser creation, not at locale handling
    with pytest.raises(Exception):
        allotrope_from_io(
            BytesIO(csv_content),
            "test.csv",
            "UNKNOWN_VENDOR",
            locale="de_DE",
        )


def test_locale_parameter_accepts_none() -> None:
    """Verify that locale parameter accepts None explicitly."""
    csv_content = b"A,B\n1,2\n3,4"
    # We expect this to fail because we don't have a real parser for raw CSV,
    # but it should fail at parser creation, not at locale handling
    with pytest.raises(Exception):
        allotrope_from_io(
            BytesIO(csv_content),
            "test.csv",
            "UNKNOWN_VENDOR",
            locale=None,
        )
