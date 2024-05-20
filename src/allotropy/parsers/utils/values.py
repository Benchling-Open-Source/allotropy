from __future__ import annotations

from dataclasses import fields
import math
import re
from typing import Any, TypeVar
from xml.etree import ElementTree

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    JsonFloat,
)
from allotropy.exceptions import AllotropeConversionError

PrimitiveValue = str | int | float


def str_to_bool(value: str) -> bool:
    return value.lower() in ("yes", "true", "t", "1")


def try_int(value: str | None, value_name: str) -> int:
    try:
        return int(assert_not_none(value, value_name))
    except ValueError as e:
        msg = f"Invalid integer string: '{value}'."
        raise AllotropeConversionError(msg) from e


def try_int_or_none(value: str | None) -> int | None:
    try:
        return int(value or "")
    except ValueError:
        return None


def try_float(value: str, value_name: str) -> float:
    assert_not_none(value, value_name)
    try:
        return float(value)
    except ValueError as e:
        msg = f"Invalid float string: '{value}'."
        raise AllotropeConversionError(msg) from e


def try_non_nan_float(value: str) -> float:
    float_value = try_non_nan_float_or_none(value)
    if float_value is None:
        msg = f"Invalid non nan float string: '{value}'."
        raise AllotropeConversionError(msg)
    return float_value


def try_non_nan_float_or_none(value: str | None) -> float | None:
    float_value = try_float_or_none(value)
    return None if float_value is None or math.isnan(float_value) else float_value


def try_float_or_none(value: str | None) -> float | None:
    try:
        return float("" if value is None else value)
    except ValueError:
        return None


def try_float_or_nan(value: str | None) -> JsonFloat:
    float_value = try_non_nan_float_or_none(value)
    return InvalidJsonFloat.NaN if float_value is None else float_value


def natural_sort_key(key: str) -> list[str]:
    """Returns a sort key that treats numeric substrings as parsed integers for comparison."""
    tokens = [token for token in re.split(r"(\d+)", key) if token]
    return [
        f"{int(token):>10}" if token.isdecimal() else token.lower() for token in tokens
    ]


T = TypeVar("T")


def assert_not_none(
    value: T | None, name: str | None = None, msg: str | None = None
) -> T:
    if value is None:
        error = msg or f"Expected non-null value{f' for {name}' if name else ''}."
        raise AllotropeConversionError(error)
    return value


def df_to_series(
    df: pd.DataFrame,
    msg: str,
) -> pd.Series[Any]:
    n_rows, _ = df.shape
    if n_rows == 1:
        return pd.Series(df.iloc[0], index=df.columns)
    raise AllotropeConversionError(msg)


def assert_df_column(df: pd.DataFrame, column: str) -> pd.Series[Any]:
    df_column = df.get(column)
    if df_column is None:
        msg = f"Unable to find column '{column}'"
        raise AllotropeConversionError(msg)
    return pd.Series(df_column)


def assert_not_empty_df(df: pd.DataFrame, msg: str) -> pd.DataFrame:
    if df.empty:
        raise AllotropeConversionError(msg)
    return df


def try_str_from_series_or_default(
    data: pd.Series[Any],
    key: str,
    default: str,
) -> str:
    value = data.get(key)
    return default if value is None else str(value)


def try_str_from_series_or_none(
    data: pd.Series[Any],
    key: str,
) -> str | None:
    value = data.get(key)
    return None if value is None else str(value)


def try_str_from_series(
    series: pd.Series[Any],
    key: str,
    msg: str | None = None,
) -> str:
    return assert_not_none(try_str_from_series_or_none(series, key), key, msg)


def try_int_from_series_or_none(
    data: pd.Series[Any],
    key: str,
) -> int | None:
    try:
        value = data.get(key)
        return try_int(str(value), key)
    except Exception as e:
        msg = f"Unable to convert '{value}' (with key '{key}') to integer value."
        raise AllotropeConversionError(msg) from e


def try_int_from_series(
    data: pd.Series[Any],
    key: str,
    msg: str | None = None,
) -> int:
    return assert_not_none(try_int_from_series_or_none(data, key), key, msg)


def try_float_from_series_or_nan(
    data: pd.Series[Any],
    key: str,
) -> JsonFloat:
    try:
        value = data.get(key)
        return try_float_or_nan(str(value))
    except Exception as e:
        msg = f"Unable to convert '{value}' (with key '{key}') to float value."
        raise AllotropeConversionError(msg) from e


def try_float_from_series_or_none(
    data: pd.Series[Any],
    key: str,
) -> float | None:
    try:
        value = data.get(key)
        return try_float_or_none(str(value))
    except Exception as e:
        msg = f"Unable to convert '{value}' (with key '{key}') to float value."
        raise AllotropeConversionError(msg) from e


def try_float_from_series(
    data: pd.Series[Any],
    key: str,
    msg: str | None = None,
) -> float:
    return assert_not_none(try_float_from_series_or_none(data, key), key, msg)


def try_bool_from_series_or_none(
    data: pd.Series[Any],
    key: str,
) -> bool | None:
    try:
        value = data.get(key)
        return None if value is None else str_to_bool(str(value))
    except Exception as e:
        msg = f"Unable to convert '{value}' (with key '{key}') to boolean value."
        raise AllotropeConversionError(msg) from e


def num_to_chars(n: int) -> str:
    d, m = divmod(n, 26)  # 26 is the number of ASCII letters
    return "" if n < 0 else num_to_chars(d - 1) + chr(m + 65)  # chr(65) = 'A'


def str_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def get_element_from_xml(
    xml_object: ElementTree.Element, tag_name: str, tag_name_2: str | None = None
) -> ElementTree.Element:
    if tag_name_2 is not None:
        tag_finder = tag_name + "/" + tag_name_2
        xml_element = xml_object.find(tag_finder)
    else:
        tag_finder = tag_name
        xml_element = xml_object.find(tag_finder)
    if xml_element is not None:
        return xml_element
    else:
        msg = f"Unable to find '{tag_finder}' from xml."
        raise AllotropeConversionError(msg)


def get_val_from_xml(
    xml_object: ElementTree.Element, tag_name: str, tag_name_2: str | None = None
) -> str:
    return str(get_element_from_xml(xml_object, tag_name, tag_name_2).text)


def get_val_from_xml_or_none(
    xml_object: ElementTree.Element, tag_name: str, tag_name_2: str | None = None
) -> str | None:
    try:
        val_from_xml = get_element_from_xml(xml_object, tag_name, tag_name_2).text
        if val_from_xml is not None:
            return str(val_from_xml)
        else:
            return None
    except AllotropeConversionError:
        return None


def get_attrib_from_xml(
    xml_object: ElementTree.Element,
    tag_name: str,
    attrib_name: str,
    tag_name_2: str | None = None,
) -> str:
    xml_element = get_element_from_xml(xml_object, tag_name, tag_name_2)
    try:
        attribute_val = xml_element.attrib[attrib_name]
        return attribute_val
    except KeyError as e:
        msg = f"Unable to find '{attrib_name}' in {xml_element.attrib}"
        raise AllotropeConversionError(msg) from e


def remove_none_fields_from_data_class(
    cls_instance: Any,
) -> Any:

    data_class_fields = fields(cls_instance.__class__)

    # get all non-none fields
    non_none_fields = {
        field.name: getattr(cls_instance, field.name)
        for field in data_class_fields
        if (getattr(cls_instance, field.name) is not None or field.default is not None)
    }

    # Create a new instance with non-None fields
    updated_instance = cls_instance.__class__(**non_none_fields)

    return updated_instance
