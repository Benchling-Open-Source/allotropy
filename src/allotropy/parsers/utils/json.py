from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import Enum
import os
import re
from typing import Any, Literal, overload, TypeVar
import warnings

from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.values import (
    assert_not_none,
    str_to_bool,
    try_float_or_none,
)

T = TypeVar("T", bool, float, int, str)
# Need to use this instead of type[T] to get mypy to realize primitive can be called to return T
Type_ = Callable[..., T]
KeyOrKeys = Iterable[str]
TypeAndKey = tuple[Type_[T], KeyOrKeys]
TypeAndKeyAndMsg = tuple[Type_[T], KeyOrKeys, str]
ValidateRaw = Callable[[Any], bool] | None


class JsonData:
    class ValidateRawMode(Enum):
        # Return None for key if raw value is None
        NOT_NONE = "NOT_NONE"

    NOT_NONE = ValidateRawMode.NOT_NONE

    @staticmethod
    def _validate_raw(v: Any, mode: ValidateRawMode | None) -> Any:
        if mode is JsonData.ValidateRawMode.NOT_NONE:
            return None if v is None else v
        return v

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = {} if data is None else data
        self.read_keys: set[str] = set()
        self.errored = False

    def __del__(self) -> None:
        if self.errored:
            return
        # NOTE: this will be turned on by default when all callers have been updated to pass the warning.
        if unread_keys := set(self.data.keys()) - self.read_keys:
            if os.getenv("WARN_UNUSED_KEYS"):
                warnings.warn(
                    f"JsonData went out of scope without reading all keys, unread: {sorted(unread_keys)}.",
                    stacklevel=2,
                )

    def _get_custom_key(self, key: str) -> float | str | None:
        if (float_value := self.get(float, key)) is not None:
            return float_value
        return self.get(str, key)

    def _get_matching_keys(self, key_or_keys: str | set[str]) -> set[str]:
        return {
            matched
            for regex_key in (
                key_or_keys if isinstance(key_or_keys, set) else {key_or_keys}
            )
            for matched in [
                k
                for k in self.data.keys()
                if k == regex_key or re.fullmatch(regex_key, k)
            ]
        }

    def get_custom_keys(
        self, key_or_keys: str | set[str]
    ) -> dict[str, float | str | None]:
        return {
            key: value
            for key in self._get_matching_keys(key_or_keys)
            if (
                value := self._validate_raw(
                    self._get_custom_key(key), JsonData.NOT_NONE
                )
            )
            is not None
        }

    def mark_read(self, key_or_keys: str | set[str]) -> None:
        self.read_keys |= self._get_matching_keys(key_or_keys)

    def get_unread(
        self, regex: str | None = None, skip: set[str] | None = None
    ) -> dict[str, Any]:
        skip = self._get_matching_keys(skip) if skip else set()
        # Mark explicitly skipped keys as "read". This not only covers the check below, but removes
        # them from the destructor warning.
        self.read_keys |= skip
        matching_keys = (
            self._get_matching_keys(regex) if regex else set(self.data.keys())
        )
        return {
            key: self.data[key]
            for key in (matching_keys - self.read_keys)
            if key in self.data
        }

    def has_key(self, key: str) -> bool:
        return key in self.data

    def __getitem__(self, type_and_key: TypeAndKey[T] | TypeAndKeyAndMsg[T]) -> T:
        """
        Get a value of the specified type with the specified key, raising an error if the
        key is not found, or if the value cannot be converted to the type.
        If a third argument is provided, it is an error message to provide if they key is not found.

        value: float = json_data[float, key]
        value: str = json_data[str, key, f"Failed to find {key} in my data"]

        Parameters:
        type (str, int, float, bool): The datatype to return.
        key (str | Iterable[str]): The key (or iterable of keys) to use to lookup.
        msg (str | None): The message to give as an error if lookup or conversion fails.

        Returns:
        type: A value of the type provided.

        Raises
        AllotropeConversionError: If the lookup or conversion to type fails.
        """
        if len(type_and_key) == 2:
            type_, key = type_and_key
            msg = None
        elif len(type_and_key) == 3:
            type_, key, msg = type_and_key
        try:
            return assert_not_none(self.get(type_, key), str(key), msg=msg)
        except Exception:
            self.errored = True
            raise

    # This overload tells typing that if default is "None" then get might return None
    @overload
    def get(
        self,
        type_: Type_[T],
        key: KeyOrKeys,
        default: Literal[None] = None,
        validate: ValidateRawMode | None = None,
    ) -> T | None:
        ...

    # This overload tells typing that if default matches T, get will return T
    @overload
    def get(
        self,
        type_: Type_[T],
        key: KeyOrKeys,
        default: T,
        validate: ValidateRawMode | None = None,
    ) -> T:
        ...

    def get(
        self,
        type_: Type_[T],
        key: KeyOrKeys,
        default: T | None = None,
        validate: ValidateRawMode | None = None,
    ) -> T | None:
        """
        Get a value of the specified type with the specified key, returning a default value if the
        key is not found, or if the value cannot be converted to the type.
        If validate is provided, it will be used to validate the raw value from the data, returning None
        if the value fails validation.

        Parameters:
        type (str, int, float, bool): The datatype to return.
        key (str | Iterable[str]): The key (or iterable of keys) to use to lookup.
        default (type | None): The value to return if lookup or conversion fails (default=None).
        validate (ValidateRawMode): The method to use for validating raw value. Defaults to (value is not None).

        Returns:
        type: A value of the type provided or default value.
        """
        if not isinstance(key, str):
            return get_first_not_none(
                lambda k: self.get(type_, k, validate=validate), key
            )
        self.read_keys.add(key)
        raw_value = self._validate_raw(self.data.get(key), validate)
        try:
            # bool needs special handling to convert
            if type_ is bool:
                raw_value = (
                    None
                    if raw_value is None
                    else ("true" if str_to_bool(str(raw_value)) else "")
                )
            if type_ is float and isinstance(raw_value, str) and "%" in raw_value:
                raw_value = raw_value.strip("%")
            convert = try_float_or_none if type_ is float else type_
            # mypy can't figure out that try_float_or_none will only be used when type_ is float.
            value = None if raw_value is None else convert(raw_value)  # type: ignore[operator]
        except ValueError:
            value = None
        return default if value is None else value

    def get_nested(
        self,
        type_: Type_[T],
        path: list[str],
        default: T | None = None,
        validate: ValidateRawMode | None = None,
    ) -> T | None:
        """
        Get a nested value following the provided path, with type conversion.

        Parameters:
        type_ (Type_[T]): The type to convert the value to
        path (list[str]): List of keys representing the path to the nested value
        default (T | None): Default value to return if path doesn't exist or conversion fails
        validate (ValidateRawMode | None): Validation mode for the raw value

        Returns:
        T | None: The typed value or the default
        """
        if not path:
            return default

        current = self.data
        for _i, key in enumerate(path[:-1]):
            if not isinstance(current, dict) or key not in current:
                return default
            current = current.get(key, {})
            # Mark the intermediate path as read
            self.mark_read(key)

        if not isinstance(current, dict) or path[-1] not in current:
            return default

        # For the final key, use the regular get method
        temp_json_data = JsonData(current)
        value = temp_json_data.get(type_, path[-1], default, validate)

        # Mark the key as read in our object
        self.mark_read(path[-1])

        return value
