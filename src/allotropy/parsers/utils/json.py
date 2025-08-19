from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import Enum
import os
import re
import traceback
from typing import Any, Literal, overload, TypeVar
import warnings

from allotropy.exceptions import AllotropeConversionError
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
        self.creation_stack = traceback.extract_stack()

    def __del__(self) -> None:
        if self.errored:
            return
        # NOTE: this will be turned on by default when all callers have been updated to pass the warning.
        if unread_keys := set(self.data.keys()) - self.read_keys:
            if os.getenv("WARN_UNUSED_KEYS"):
                # Find the creation point in the stack (skip the JsonData.__init__ frame)
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
                    f"JsonData went out of scope without reading all keys{creation_info}, unread: {sorted(unread_keys)}.",
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

        # Get all unread keys
        all_unread_keys = {
            key for key in (matching_keys - self.read_keys) if key in self.data
        }

        # Filter to only include keys with non-dict, non-list values
        unread_keys = {}
        for key in all_unread_keys:
            value = self.data[key]
            # Ignore nested dictionaries and lists - these should be handled explicitly
            if not isinstance(value, dict | list):
                unread_keys[key] = value

        if all_unread_keys:
            self.read_keys |= all_unread_keys

        return unread_keys

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
        if isinstance(type_and_key, str):
            key = type_and_key
            value = self.data.get(key)
            if value is None:
                msg = f"Required field '{key}' not found in data"
                raise AllotropeConversionError(msg)
            return value

        # Handle the case where type, key (and optionally message) are provided
        if len(type_and_key) == 2:
            type_, key = type_and_key
            msg = None
        elif len(type_and_key) == 3:
            type_, key, msg = type_and_key
        else:
            msg = f"Invalid arguments to __getitem__: {type_and_key}"
            raise AllotropeConversionError(msg)

        try:
            result = assert_not_none(self.get(type_, key), str(key), msg=msg)
            return result
        except Exception as e:
            self.errored = True
            # Wrap any exception with AllotropeConversionError
            msg = msg or f"Error accessing field '{key}': {e!s}"
            raise AllotropeConversionError(msg) from e

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

    def get_keys_as_dict(
        self,
        field_mappings: dict[str, tuple[Any, str, Any | None]],
        skip: set[str] | None = None,
        include_unread: bool | None = None,
    ) -> dict[str, Any]:
        """
        Extract multiple fields from JsonData into a dictionary, with type conversion.

        Example:
            field_mappings = {
                "output_field1": (str, "input_field1", None),  # type, field name, default value
                "output_field2": (float, "input_field2", 0.0),
                "renamed_field": (int, "original_name", None),
            }
            result = json_data.get_keys_as_dict(field_mappings)

        Parameters:
        field_mappings: Mapping of output field names to tuples of (type, input field name, default)
                        If default value is None, the field will be omitted if not found
        skip: Set of field names to skip when including unread data
        include_unread: Whether to include unread fields in the result (keyword-only)

        Returns:
        Dictionary with extracted fields, filtered to remove None values
        """
        result = {}

        # Process explicit field mappings
        for output_field, (field_type, input_field, default) in field_mappings.items():
            value = self.get(field_type, input_field, default)
            if value is not None or (default is not None and field_type is not float):
                result[output_field] = value

        # Include unread fields if requested
        if include_unread:
            result.update(self.get_unread(skip=skip))

        # Filter out None values and empty strings
        return {k: v for k, v in result.items() if v is not None and v != ""}

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
