from __future__ import annotations

from collections.abc import Callable
import math
import re
from typing import Any, TypeVar

from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    JsonFloat,
    TQuantityValue,
    TStatisticDatumRole,
)
from allotropy.exceptions import AllotropeConversionError, AllotropyParserError
from allotropy.parsers.utils.units import get_quantity_class

PrimitiveValue = str | int | float


def str_to_bool(value: str) -> bool:
    return value.lower() in ("yes", "y", "true", "t", "1")


def try_int(value: str | None, value_name: str) -> int:
    str_value = assert_not_none(value, value_name)
    try:
        return int(str_value)
    except ValueError as e:
        # If the value is expected to be an int, but represented as a float (e.g. 1.0) try casting with float
        # and return if it's a valid int.
        try:
            float_value = _try_float(str_value)
            if float_value == int(float_value):
                return int(float_value)
        except ValueError:
            pass
        msg = f"Invalid integer string: '{value}'."
        raise AllotropeConversionError(msg) from e


def try_int_or_none(value: str | None) -> int | None:
    try:
        return int(value or "")
    except ValueError:
        return None


def _try_float(value: str | float | None) -> float:
    if isinstance(value, float):
        return value
    # NOTE: this will convert a string with commas for thousands into a decimal, potentially introducing
    # an unexpected error, e.g. one thousand represented as 1,000 would get converted to 1.0
    # However, numbers are not usually represented like this in scientific output (we have no example of it)
    return float(str(value).replace(",", "."))


def try_float(value: str | float | None, value_name: str) -> float:
    assert_not_none(value, value_name)
    try:
        return _try_float(value)
    except ValueError as e:
        msg = f"Invalid float string: '{value}'."
        raise AllotropeConversionError(msg) from e


def try_float_or_none(value: str | float | None) -> float | None:
    try:
        return _try_float(str(value))
    except ValueError:
        return None


def try_nan_float_or_none(value: str | float | None) -> JsonFloat | None:
    float_value = try_float_or_none(value) if isinstance(value, str) else value
    if float_value is None:
        return None
    return InvalidJsonFloat.NaN if math.isnan(float_value) else float_value


def try_non_nan_float_or_none(value: str | float | None) -> float | None:
    float_value = try_float_or_none(value)
    return None if float_value is None or math.isnan(float_value) else float_value


def try_non_nan_float(value: str) -> float:
    float_value = try_non_nan_float_or_none(value)
    if float_value is None:
        msg = f"Invalid non nan float string: '{value}'."
        raise AllotropeConversionError(msg)
    return float_value


def try_int_or_nan(value: str | int | None) -> int | InvalidJsonFloat:
    if isinstance(value, int):
        return value
    float_value = try_non_nan_float_or_none(value)
    return InvalidJsonFloat.NaN if float_value is None else int(float_value)


def try_float_or_nan(value: str | float | None) -> JsonFloat:
    float_value = try_non_nan_float_or_none(value)
    return InvalidJsonFloat.NaN if float_value is None else float_value


def natural_sort_key(key: str) -> list[str]:
    """Returns a sort key that treats numeric substrings as parsed integers for comparison."""
    tokens = [token for token in re.split(r"(\d+)", key) if token]
    return [
        f"{int(token):>10}" if token.isdecimal() else token.lower() for token in tokens
    ]


QuantityType = TypeVar("QuantityType", bound=TQuantityValue)


def quantity_or_none(
    value_cls: type[QuantityType],
    value: JsonFloat | list[JsonFloat] | list[int] | None,
    index: int | None = None,
    has_statistic_datum_role: TStatisticDatumRole | None = None,
) -> QuantityType | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value_cls(value=value[assert_not_none(index, msg="Cannot provide list to quantity_or_none without index")])  # type: ignore[call-arg]
    # Typing does not know that all subclasses of TQuantityValue have default value for unit set.
    return value_cls(value=value, has_statistic_datum_role=has_statistic_datum_role)  # type: ignore[call-arg]


def quantity_or_none_from_unit(
    unit: str | None,
    value: JsonFloat | list[JsonFloat] | list[int] | None,
) -> TQuantityValue | None:
    if value is None:
        return None
    value_cls = get_quantity_class(unit)
    if not value_cls:
        msg = f"Must provide valid unit when value is non-null, got: {unit}"
        raise AllotropyParserError(msg)
    return quantity_or_none(value_cls, value)


T = TypeVar("T")


def assert_not_none(
    value: T | None, name: str | None = None, msg: str | None = None
) -> T:
    if value is None:
        msg = msg or f"Expected non-null value{f' for {name}' if name else ''}."
        raise AllotropeConversionError(msg)
    return value


Type_ = Callable[..., T]


def assert_is_type(value: Any, type_: Type_[T], msg: str | None = None) -> T:
    if type(value) is not type_:
        msg = msg or f"Expected value: '{value}' to be of type {type_}"
        raise AllotropeConversionError(msg)
    return value  # type:ignore[no-any-return]


def num_to_chars(n: int) -> str:
    d, m = divmod(n, 26)  # 26 is the number of ASCII letters
    return "" if n < 0 else num_to_chars(d - 1) + chr(m + 65)  # chr(65) = 'A'


def str_or_none(value: Any) -> str | None:
    return None if value is None else str(value)
