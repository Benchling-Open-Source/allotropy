from collections.abc import Collection
from typing import Any, Optional


class AllotropeConversionError(Exception):
    pass


def msg_for_error_on_unrecognized_value(
    key: str, value: Any, valid_values: Optional[Collection[Any]] = None
) -> str:
    msg = f"Unrecognized {key}: '{value}'."
    if valid_values:
        msg += f" Only {sorted(valid_values)} are supported."
    return msg
