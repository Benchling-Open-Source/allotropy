from typing import Optional

import pytest

from allotropy.parsers.utils.values import (
    assert_not_none,
    natural_sort_key,
    try_float,
    try_int,
    value_or_none,
)


def test_assert_not_none() -> None:
    x = 3
    assert assert_not_none(x) == x


def test_assert_not_none_fails() -> None:
    with pytest.raises(Exception, match="^Expected non-null value$"):
        assert_not_none(None)


def test_assert_not_none_fails_with_message() -> None:
    with pytest.raises(Exception, match="^param_name was None$"):
        assert_not_none(None, msg="param_name was None")


def test_assert_not_none_fails_with_name() -> None:
    with pytest.raises(Exception, match="^Expected non-null value for param_name$"):
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
def test_try_float(value: Optional[str], expected: Optional[int]) -> None:
    assert try_float(value) == expected


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
def test_try_int(value: Optional[str], expected: Optional[float]) -> None:
    assert try_int(value) == expected


@pytest.mark.short
@pytest.mark.parametrize(
    "value,expected",
    [
        ("", None),
        ("  ", None),
        (" 1 ", "1"),
    ],
)
def test_value_or_none(value: str, expected: Optional[str]) -> None:
    assert value_or_none(value) == expected
