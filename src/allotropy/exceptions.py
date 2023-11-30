from collections.abc import Collection
from typing import Any


class AllotropeConversionError(Exception):
    pass


def msg_for_error_on_unrecognized_value(
    key: str, value: Any, valid_values: Collection
) -> str:
    return f"Unrecognized {key}: {value}. Only {sorted(valid_values)} are supported."
