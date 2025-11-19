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


def test_get_set_of_keys_untyped() -> None:
    d = DictData({"a": 1, "b": 2, "c": None})
    res = d.get(key={"a", "c", "missing"})
    # Includes only present keys, preserving None values
    assert res == {"a": 1, "c": None}
    assert "a" in d.keys_read() and "c" in d.keys_read()


def test_get_set_of_keys_typed() -> None:
    d = DictData({"x": "1.0", "y": "bad", "z": None})
    res = d.get(float, {"x", "y", "z", "none"})
    # Only successfully converted values are included
    assert res == {"x": pytest.approx(1.0)}
    # Ensure read marking for attempted keys present
    assert "x" in d.keys_read()


def test_get_keys_as_dict_behavior() -> None:
    d = DictData({"conc": "12.5%", "sampleId": "S001", "user": "alice", "empty": ""})
    field_mappings = {
        "concentration": (float, "conc", None),
        "sample_id": (str, "sampleId", None),
        "operator": (str, "user", None),
        "missing_with_default": (int, "missing", 0),
        "empty_value": (str, "empty", None),
    }
    res = d.get_keys_as_dict(field_mappings)
    assert res["concentration"] == pytest.approx(12.5)
    assert res["sample_id"] == "S001"
    assert res["operator"] == "alice"
    assert res["missing_with_default"] == 0
    # Empty strings should be filtered out
    assert "empty_value" not in res
    # Read marking for keys that were actually looked up and present
    assert {"conc", "sampleId", "user"}.issubset(d.keys_read())
    # Missing key with default should not be marked as read
    assert "missing" not in d.keys_read()


def test_get_unread_with_key_str() -> None:
    d = DictData({"a": 1, "b": 2, "nested": {"x": 3}})
    # Initially unread, should return only scalar 'a'
    res = d.get_unread("a")
    assert res == {"a": 1}
    # Marked as read; second call should return empty
    assert d.get_unread("a") == {}
    # Nested dicts should be excluded
    assert d.get_unread("nested") == {}


def test_get_unread_with_key_set() -> None:
    d = DictData({"a": 1, "b": 2, "c": 3})
    # Read one key first to verify filtering of already-read keys
    _ = d.get(int, "b")
    res = d.get_unread({"a", "b", "missing"})
    assert res == {"a": 1}
    # Keys returned are now marked as read
    assert d.get_unread({"a"}) == {}


def test_mark_read_accepts_single_and_set() -> None:
    d = DictData({"a": 1, "b": 2})
    d.mark_read("a")
    assert "a" in d.keys_read()
    d.mark_read({"b"})
    assert {"a", "b"}.issubset(d.keys_read())


def test_mark_read_ignores_non_string_in_set() -> None:
    d = DictData({})
    d.mark_read({"a", 1})  # type: ignore[arg-type]
    assert "a" in d.keys_read()


def test_get_unread_skip_behavior_all() -> None:
    d = DictData({"a": 1, "b": 2, "c": 3})
    res = d.get_unread(skip={"b"})
    assert res == {"a": 1, "c": 3}
    # 'b' should remain unread
    assert "b" not in d.keys_read()
    # Returned keys should be marked as read
    assert {"a", "c"}.issubset(d.keys_read())


def test_get_unread_skip_with_key_set() -> None:
    d = DictData({"a": 1, "b": 2, "c": 3})
    res = d.get_unread({"a", "b"}, skip={"b"})
    assert res == {"a": 1}
    assert "b" not in d.keys_read()
