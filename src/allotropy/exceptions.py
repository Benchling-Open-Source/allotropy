from collections.abc import Collection
from enum import Enum
from typing import Any, TypeVar


# Base exception for errors raised by allotropy.
class AllotropyError(Exception):
    ...


# Unexpected error when reading input data.
class AllotropeParsingError(AllotropyError):
    ...


# Unexpected error when validating output against schema.
class AllotropeValidationError(AllotropyError):
    ...


# Unexpected error when converting allotropy dataclass model to json.
class AllotropeSerializationError(AllotropyError):
    ...


# Expected error caused by a programming error, indicating a bug.
class AllotropyParserError(AllotropyError):
    ...


# Expected error caused by bad input data, with a message telling user what the problem is.
class AllotropeConversionError(AllotropyError):
    ...


def list_values(values: Collection[Any] | type[Enum]) -> list[str]:
    return sorted([str(v.value if isinstance(v, Enum) else v) for v in values])


T = TypeVar("T")


def valid_value_or_raise(
    name: str, values: set[T], valid_values: Collection[T] | type[Enum]
) -> T:
    if len(values) == 1:
        return values.pop()
    msg = f"Could not infer {name}, expecting exactly one of {list_values(valid_values)}, found {list_values(values)}"
    raise AllotropeConversionError(msg)


def get_key_or_error(name: str, key: str, mapping: dict[str, T]) -> T:
    try:
        return mapping[key]
    except KeyError as e:
        msg = msg_for_error_on_unrecognized_value(name, key, mapping.keys())
        raise AllotropeConversionError(msg) from e


def msg_for_error_on_unrecognized_value(
    name: str, value: T, valid_values: Collection[T] | type[Enum] | None = None
) -> str:
    msg = f"Unrecognized {name}: '{value}'."
    if valid_values:
        msg += f" Expecting one of {list_values(valid_values)}."
    return msg
