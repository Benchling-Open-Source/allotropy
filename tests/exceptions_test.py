import re

import pytest

from allotropy.exceptions import (
    AllotropeConversionError,
    get_key_or_error,
    list_values,
    valid_value_or_raise,
)
from allotropy.parsers.revvity_kaleido.kaleido_structure import ExperimentType


def test_list_values() -> None:
    assert list_values(["XYZ", "ABC"]) == ["ABC", "XYZ"]


def test_list_values_enum() -> None:
    assert list_values(ExperimentType) == [
        "absorbance",
        "fluorescence",
        "luminescence",
        "optical imaging",
    ]


def test_valid_values_or_raise() -> None:
    valid_value_or_raise("something", {"some value"}, {"some value", "other value"})

    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            "Could not infer something, expecting exactly one of ['other value', 'some value'], found []"
        ),
    ):
        valid_value_or_raise("something", set(), {"some value", "other value"})

    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            "Could not infer something, expecting exactly one of ['other value', 'some value'], found ['other value', 'some value']"
        ),
    ):
        valid_value_or_raise(
            "something", {"some value", "other value"}, {"some value", "other value"}
        )


def test_get_key_or_error() -> None:
    assert get_key_or_error("something", "good_key", {"good_key": 1}) == 1

    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            "Unrecognized something: 'bad_key'. Expecting one of ['good_key']."
        ),
    ):
        get_key_or_error("something", "bad_key", {"good_key": 1})
