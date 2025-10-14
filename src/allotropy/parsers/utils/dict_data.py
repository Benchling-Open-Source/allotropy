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
        for key, value in data.items():
            super().__setitem__(key, self._wrap(value))

    def _wrap(self, value: Any) -> Any:
        if isinstance(value, dict):
            return DictData(value)
        if isinstance(value, list):
            return [self._wrap(v) for v in value]
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

    def get(self, *args: Any, **kwargs: Any) -> Any:
        """
        Get a value either by key (dict-style) or by specifying a type and key.

        Usage:
        - get(key: str, default: Any | None = None) -> Any | None
        - get(type_: type, key: str, default: Any | None = None) -> Any | None

        """
        # Determine mode and normalize args
        is_typed_mode = ("type_" in kwargs) or (
            len(args) >= 1 and not isinstance(args[0], str)
        )

        if not is_typed_mode:
            # Dict-style usage: get(key, default?) or get(key=..., default=...)
            key_local = kwargs.get("key", args[0] if len(args) >= 1 else None)
            default_local = kwargs.get("default", args[1] if len(args) >= 2 else None)
            if not isinstance(key_local, str):
                msg = "Dict-style get requires 'key' to be a str."
                raise AllotropeConversionError(msg)
            if key_local in self:
                self._read_keys.add(key_local)
            return super().get(key_local, default_local)

        # Typed mode: type_, key, default via kwargs or args
        type_ = kwargs.get("type_", args[0] if len(args) >= 1 else None)
        key_local = kwargs.get("key", args[1] if len(args) >= 2 else None)
        default_local = kwargs.get("default", args[2] if len(args) >= 3 else None)
        if not isinstance(key_local, str):
            msg = (
                "When calling get with a type as first argument, the second "
                "argument must be the key (str)."
            )
            raise AllotropeConversionError(msg)

        if key_local not in self:
            return default_local
        # Mark as read regardless of convert success
        self._read_keys.add(key_local)
        raw_value = super().get(key_local)

        # Special handling for containers
        if type_ in (dict, DictData):
            if isinstance(raw_value, DictData):
                value: Any = raw_value
            elif isinstance(raw_value, dict):
                value = DictData(raw_value)
            else:
                value = None
            return default_local if value is None else value

        if type_ is list:
            if isinstance(raw_value, list):
                return raw_value
            return default_local

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
                value = (
                    None if converted_raw is None else try_float_or_none(converted_raw)
                )
            else:
                value = None if converted_raw is None else type_(converted_raw)
        except ValueError:
            value = None

        return default_local if value is None else value

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

    def keys_read(self) -> set[str]:
        return set(self._read_keys)

    def keys_unread(self) -> set[str]:
        return set(self.keys()) - self._read_keys

    def mark_read(self, key: str) -> None:
        self._read_keys.add(key)

    def get_unread(self) -> dict[str, Any]:
        """
        Return a mapping of unread keys to their values, excluding nested
        dictionaries and lists (which should be handled explicitly).
        """
        unread: dict[str, Any] = {}
        for key, value in self.items():
            if key in self._read_keys:
                continue
            if isinstance(value, dict | list):
                continue
            unread[key] = value
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

    # Mutation APIs (not expected to be used, but kept consistent)
    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, self._wrap(value))

    # Convenience helpers
    @staticmethod
    def from_any(value: Any) -> Any:
        """
        Recursively convert dictionaries inside the given value into
        DictData instances.
        """
        if isinstance(value, dict):
            return DictData(value)
        if isinstance(value, list):
            return [DictData.from_any(v) for v in value]
        return value
