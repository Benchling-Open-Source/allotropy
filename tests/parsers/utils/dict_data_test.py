from __future__ import annotations

import pytest

from allotropy.parsers.utils.dict_data import DictData


def test_dict_style_get_read_and_default() -> None:
    d = DictData({"a": 1})
    assert d.get("a") == 1
    assert d.get("missing", 42) == 42
    assert "a" in d.keys_read()


def test_typed_get_scalar_conversions() -> None:
    d = DictData({"b": "true", "c": "12.5", "d": "7"})
    assert d.get(bool, "b") is True
    assert d.get(float, "c") == pytest.approx(12.5)
    assert d.get(int, "d") == 7


def test_typed_get_container_wrapping() -> None:
    d = DictData({"nested": {"x": 1}, "arr": [{"y": 2}, 3]})
    nested = d.get(DictData, "nested")
    assert isinstance(nested, DictData)
    assert nested.get(int, "x") == 1

    arr = d.get(list, "arr", [])
    assert isinstance(arr, list)
    assert isinstance(arr[0], DictData)
    assert arr[0].get(int, "y") == 2


def test_get_unread_and_get_unread_deep() -> None:
    d = DictData(
        {
            "a": 1,
            "nested": {"x": 2, "inner": {"z": 3}},
            "arr": [{"y": 4}, {"k": 5}],
        }
    )

    # Shallow unread excludes containers
    unread = d.get_unread()
    assert unread == {"a": 1}

    deep = d.get_unread_deep()
    # After deep read, nested leaves should be captured
    assert deep == {"nested": {"x": 2, "inner": {"z": 3}}, "arr": [{"y": 4}, {"k": 5}]}


def test_wrap_value_wraps_dicts_and_lists() -> None:
    value = {"a": {"b": 1}, "c": [{"d": 2}, 3]}
    helper = DictData({})
    wrapped = helper._wrap_value(value)
    assert isinstance(wrapped, DictData)
    assert isinstance(wrapped.get(DictData, "a"), DictData)
    arr = wrapped.get(list, "c")
    assert isinstance(arr, list)
    assert isinstance(arr[0], DictData)


def test_get_nested_returns_dictdata_and_marks_read() -> None:
    d = DictData({"nested": {"x": 1}})

    # Existing key returns a DictData and marks key as read
    nested = d.get_nested("nested")
    assert isinstance(nested, DictData)
    assert nested.get(int, "x") == 1
    assert "nested" in d.keys_read()

    # Missing key returns empty DictData and does not mark as read
    missing = d.get_nested("missing")
    assert isinstance(missing, DictData)
    assert missing == DictData({})
    assert "missing" not in d.keys_read()
