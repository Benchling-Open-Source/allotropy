from __future__ import annotations

from collections.abc import Callable
import os
import traceback
from typing import Any, Literal, overload, TypeVar
import warnings

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import (
    str_to_bool,
    try_float_or_none,
)

T = TypeVar("T", bool, float, int, str, dict[Any, Any], list[Any])
Type_ = Callable[[Any], T]


class DictData(dict[str, Any]):
    """
    A dict subclass that tracks which keys have been accessed.

    - Recursively wraps nested dictionaries into DictData
      and lists of dictionaries into lists of DictData.
    - The instance is read-only by convention for this use case; we assume
      no mutations after construction, but basic mutation APIs are still
      supported and will maintain invariants for safety.
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        if data is None:
            data = {}
        if not isinstance(data, dict):
            msg = f"Expected dict, got {type(data)}"
            raise AllotropeConversionError(msg)
        super().__init__()
        self._read_keys: set[str] = set()
        self.errored = False
        self.creation_stack = traceback.extract_stack()
        self._load_dict(data)

    def _load_dict(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            super().__setitem__(key, self._wrap_value(value))

    def _wrap_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return DictData(value)
        if isinstance(value, list):
            return [self._wrap_value(v) for v in value]
        return value

    # Reading APIs
    def __getitem__(self, key: str) -> Any:
        self._read_keys.add(key)
        return super().__getitem__(key)

    # Overloads to support both dict-style and typed retrieval
    @overload
    def get(self, key: str, default: Any | None = None) -> Any | None:
        ...

    @overload
    def get(
        self,
        key: set[str],
    ) -> dict[str, Any]:
        ...

    @overload
    def get(
        self,
        type_: type[DictData],
        key: str,
        default: Literal[None] = None,
    ) -> DictData | None:
        ...

    @overload
    def get(
        self,
        type_: type[DictData],
        key: str,
        default: DictData,
    ) -> DictData:
        ...

    @overload
    def get(
        self,
        type_: type[list[Any]],
        key: str,
        default: Literal[None] = None,
    ) -> list[Any] | None:
        ...

    @overload
    def get(
        self,
        type_: type[list[Any]],
        key: str,
        default: list[Any],
    ) -> list[Any]:
        ...

    @overload
    def get(
        self,
        type_: Type_[T],
        key: str,
        default: Literal[None] = None,
    ) -> T | None:
        ...

    @overload
    def get(
        self,
        type_: Type_[T],
        key: str,
        default: T,
    ) -> T:
        ...

    @overload
    def get(
        self,
        type_: Type_[T],
        key: set[str],
    ) -> dict[str, T]:
        ...

    def get(self, *args: Any, **kwargs: Any) -> Any:
        """
        Get a value either by key (dict-style) or by specifying a type and key.

        Usage:
        - get(key: str, default: Any | None = None) -> Any | None
        - get(type_: type, key: str, default: Any | None = None) -> Any | None
        - get(key: set[str]) -> dict[str, Any]
        - get(type_: type, key: set[str]) -> dict[str, Any]

        """
        # Determine mode and normalize args
        is_typed_mode = ("type_" in kwargs) or (
            len(args) >= 1 and not isinstance(args[0], str)
        )

        if not is_typed_mode:
            # Dict-style usage: get(key, default?) or get(key=..., default=...)
            key_local = kwargs.get("key", args[0] if len(args) >= 1 else None)
            default_local = kwargs.get("default", args[1] if len(args) >= 2 else None)
            if isinstance(key_local, set):
                return self._get_raw_many(key_local)
            if not isinstance(key_local, str):
                msg = "Dict-style get requires 'key' to be a str."
                raise AllotropeConversionError(msg)
            return self._get_raw(key_local, default_local)

        # Typed mode: type_, key, default via kwargs or args
        type_ = kwargs.get("type_", args[0] if len(args) >= 1 else None)
        key_local = kwargs.get("key", args[1] if len(args) >= 2 else None)
        default_local = kwargs.get("default", args[2] if len(args) >= 3 else None)
        if isinstance(key_local, set):
            return self._get_typed_many(type_, key_local)
        if not isinstance(key_local, str):
            msg = (
                "When calling get with a type as first argument, the second "
                "argument must be the key (str)."
            )
            raise AllotropeConversionError(msg)
        return self._get_typed(type_, key_local, default_local)

    # --- Simplified helper APIs ---
    def _get_raw(self, key: str, default: Any | None = None) -> Any | None:
        if not isinstance(key, str):
            msg = "get_raw requires 'key' to be a str."
            raise AllotropeConversionError(msg)
        if key in self:
            self._read_keys.add(key)
        return super().get(key, default)

    def _get_raw_many(self, keys: set[str]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k in keys:
            if isinstance(k, str) and k in self:
                self._read_keys.add(k)
                result[k] = super().get(k)
        return result

    def _convert_typed(self, type_: Any, raw_value: Any) -> Any | None:
        # Special handling for containers
        if type_ in (dict, DictData):
            if isinstance(raw_value, DictData):
                return raw_value
            if isinstance(raw_value, dict):
                return DictData(raw_value)
            return None
        if type_ is list:
            return raw_value if isinstance(raw_value, list) else None

        # Scalar conversions mirror JsonData.get behavior
        try:
            converted_raw = raw_value
            if type_ is bool:
                converted_raw = (
                    None
                    if raw_value is None
                    else ("true" if str_to_bool(str(raw_value)) else "")
                )
            if (
                type_ is float
                and isinstance(converted_raw, str)
                and "%" in converted_raw
            ):
                converted_raw = converted_raw.strip("%")
            if type_ is float:
                return (
                    None if converted_raw is None else try_float_or_none(converted_raw)
                )
            return None if converted_raw is None else type_(converted_raw)
        except ValueError:
            return None

    def _get_typed(
        self, type_: Any, key: str, default: Any | None = None
    ) -> Any | None:
        if not isinstance(key, str):
            msg = "get_typed requires 'key' to be a str."
            raise AllotropeConversionError(msg)
        if key not in self:
            return default
        # Mark as read regardless of convert success
        self._read_keys.add(key)
        raw_value = super().get(key)
        value = self._convert_typed(type_, raw_value)
        return default if value is None else value

    def _get_typed_many(self, type_: Any, keys: set[str]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k in keys:
            if not isinstance(k, str):
                continue
            value = self._get_typed(type_, k, None)
            if value is not None:
                result[k] = value
        return result

    def __del__(self) -> None:
        if self.errored:
            return
        unread_keys = set(self.keys()) - self._read_keys
        if unread_keys:
            if os.getenv("WARN_UNUSED_KEYS"):
                creation_point = None
                for frame in reversed(self.creation_stack):
                    if frame.name != "__init__" or "json.py" not in frame.filename:
                        creation_point = (
                            f"{frame.filename}:{frame.lineno} in {frame.name}"
                        )
                        break
                creation_info = (
                    f" (created at {creation_point})" if creation_point else ""
                )
                warnings.warn(
                    f"DictData went out of scope without reading all keys{creation_info}, unread: {sorted(unread_keys)}.",
                    stacklevel=2,
                )

    def get_nested(self, key: str) -> DictData:
        """Get nested dict for safe chaining."""
        return self.get(DictData, key, DictData())

    def keys_read(self) -> set[str]:
        return set(self._read_keys)

    def keys_unread(self) -> set[str]:
        return set(self.keys()) - self._read_keys

    def mark_read(self, key: str | set[str]) -> None:
        if isinstance(key, str):
            self._read_keys.add(key)
            return
        if isinstance(key, set):
            for k in key:
                if isinstance(k, str):
                    self._read_keys.add(k)
            return

    def mark_read_deep(self, key: str | set[str]) -> None:
        """
        Mark the provided key(s) as read and recursively mark all nested keys
        as read for any child DictData values (including those inside lists).
        """
        # Normalize to a set of keys
        if isinstance(key, str):
            keys_to_mark: set[str] = {key}
        elif isinstance(key, set):
            keys_to_mark = {k for k in key if isinstance(k, str)}
        else:
            msg = "mark_read_deep expects a str or set[str]."
            raise AllotropeConversionError(msg)

        for k in keys_to_mark:
            # Mark the key at this level
            self._read_keys.add(k)
            if k not in self:
                continue
            value = super().get(k)
            # Recurse into nested DictData
            if isinstance(value, DictData):
                value.mark_read_deep(set(value.keys()))
            # Recurse into lists of DictData
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, DictData):
                        item.mark_read_deep(set(item.keys()))

    def get_unread(
        self, key: str | set[str] | None = None, skip: set[str] | None = None
    ) -> dict[str, Any]:
        """
        Return a mapping of unread keys to their values, excluding nested
        dictionaries and lists (which should be handled explicitly).

        If `key` is provided (str or set[str]), only return those keys that are
        currently unread and present (with non-container values). Matched keys
        are marked as read.
        """
        unread: dict[str, Any] = {}
        # Normalize skip set (tolerate non-str entries)
        skip_set: set[str] = set()
        if skip is not None:
            skip_set = {s for s in skip if isinstance(s, str)}

        if key is None:
            for k, value in self.items():
                if k in self._read_keys or k in skip_set:
                    continue
                if isinstance(value, dict | list):
                    continue
                unread[k] = value
            if unread:
                self._read_keys.update(unread.keys())
            return unread

        keys_to_check: set[str]
        if isinstance(key, str):
            keys_to_check = {key}
        elif isinstance(key, set):
            keys_to_check = {k for k in key if isinstance(k, str)}
        else:
            msg = "key must be str | set[str] | None"
            raise AllotropeConversionError(msg)

        for k in keys_to_check:
            if k in skip_set:
                continue
            if k in self._read_keys:
                continue
            if k not in self:
                continue
            value = super().get(k)
            if isinstance(value, dict | list):
                continue
            unread[k] = value

        if unread:
            self._read_keys.update(unread.keys())
        return unread

    def get_unread_deep(self) -> dict[str, Any]:
        """
        Recursively collect unread, non-container values from this dictionary and
        any nested dictionaries (including those inside lists).

        - Returns a nested structure containing only unread leaves.
        - Marks keys as read where values are returned.
        """
        result: dict[str, Any] = {}

        for key, value in self.items():
            # Recurse into nested dict-like values
            if isinstance(value, DictData):
                nested_unread = value.get_unread_deep()
                if nested_unread:
                    result[key] = nested_unread
                    self._read_keys.add(key)
                continue

            # Traverse lists to find unread content inside nested dicts
            if isinstance(value, list):
                any_unread = False
                collected_list: list[Any] = []
                for item in value:
                    if isinstance(item, DictData):
                        nested = item.get_unread_deep()
                        if nested:
                            any_unread = True
                            collected_list.append(nested)
                        else:
                            collected_list.append({})
                    else:
                        # Non-dict/list items inside list are not tracked per-key; omit
                        continue
                if any_unread:
                    result[key] = collected_list
                    self._read_keys.add(key)
                continue

            # Leaf scalar
            if key not in self._read_keys:
                result[key] = value
                self._read_keys.add(key)

        return result

    def get_keys_as_dict(
        self,
        field_mappings: dict[str, tuple[Any, str, Any | None]],
    ) -> dict[str, Any]:
        """
        Extract multiple fields into a dictionary using output key renaming,
        with type conversion and per-field defaults.

        This mirrors JsonData.get_keys_as_dict semantics, but operates on
        DictData and marks matched keys as read via DictData.get.

        Example:
            field_mappings = {
                "output_field1": (str, "input_field1", None),
                "output_field2": (float, "input_field2", 0.0),
                "renamed_field": (int, "original_name", None),
            }
            result = dict_data.get_keys_as_dict(field_mappings)

        """
        result: dict[str, Any] = {}

        for output_field, (
            field_type,
            input_field,
            per_field_default,
        ) in field_mappings.items():
            value = self.get(field_type, input_field, per_field_default)
            if value is not None or (
                per_field_default is not None and field_type is not float
            ):
                result[output_field] = value

        # Filter out None values and empty strings, matching JsonData.get_keys_as_dict behavior
        return {k: v for k, v in result.items() if v is not None and v != ""}

    # Mutation APIs (not expected to be used, but kept consistent)
    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, self._wrap_value(value))
