from typing import Optional

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import (
    assert_not_none,
    natural_sort_key,
    try_float,
    try_float_or_none,
    try_int,
    try_int_or_none,
)


def test_assert_not_none() -> None:
    x = 3
    assert assert_not_none(x) == x


def test_assert_not_none_fails() -> None:
    with pytest.raises(Exception, match="^Expected non-null value.$"):
        assert_not_none(None)


def test_assert_not_none_fails_with_message() -> None:
    with pytest.raises(Exception, match="^param_name was None$"):
        assert_not_none(None, msg="param_name was None")


def test_assert_not_none_fails_with_name() -> None:
    with pytest.raises(Exception, match="^Expected non-null value for param_name.$"):
        assert_not_none(None, "param_name")


def test_assert_not_none_fails_with_message_and_name() -> None:
    with pytest.raises(Exception, match="^param_name was None$"):
        assert_not_none(None, "param_name", "param_name was None")


@pytest.mark.short
@pytest.mark.parametrize(
    "key,expected",
    [
        ("", []),
        ("a", ["a"]),
        ("1", ["         1"]),
        ("a1b2c", ["a", "         1", "b", "         2", "c"]),
    ],
)
def test_natural_sort_key(key: str, expected: list[str]) -> None:
    assert natural_sort_key(key) == expected


def _try_float(value: str) -> float:
    return try_float(value, "param")


def test_try_float() -> None:
    assert _try_float("1.0") == 1.0


@pytest.mark.short
@pytest.mark.parametrize(
    "value,expected_regex",
    [
        (None, "Expected non-null value for param."),
        ("a", "Invalid float string: 'a'."),
    ],
)
def test_try_float_fails(value: str, expected_regex: str) -> None:
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        _try_float(value)


@pytest.mark.short
@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("1", 1),
        ("1.1", 1.1),
    ],
)
def test_try_float_or_none(value: Optional[str], expected: Optional[int]) -> None:
    assert try_float_or_none(value) == expected


def _try_int(value: Optional[str]) -> int:
    return try_int(value, "param")


def test_try_int() -> None:
    assert _try_int("1") == 1


@pytest.mark.short
@pytest.mark.parametrize(
    "value,expected_regex",
    [
        (None, "Expected non-null value for param."),
        ("a", "Invalid integer string: 'a'."),
    ],
)
def test_try_int_fails(value: Optional[str], expected_regex: str) -> None:
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        _try_int(value)


@pytest.mark.short
@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("1", 1),
        ("1.1", None),
    ],
)
def test_try_int_or_none(value: Optional[str], expected: Optional[float]) -> None:
    assert try_int_or_none(value) == expected
