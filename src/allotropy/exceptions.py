from collections.abc import Collection
from typing import Any

_ERROR_MESSAGE = "message must not be empty"


class AllotropeConversionError(Exception):
    def __init__(self, message: str) -> None:
        if not message or not message.strip():
            raise ValueError(_ERROR_MESSAGE)
        super().__init__(message)


def msg_for_error_on_unrecognized_value(
    key: str, value: Any, valid_values: Collection[Any] | None = None
) -> str:
    msg = f"Unrecognized {key}: '{value}'."
    if valid_values:
        msg += f" Only {sorted(valid_values)} are supported."
    return msg
