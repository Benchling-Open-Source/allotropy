from collections.abc import Collection
from typing import Any, Optional

_ERROR_MESSAGE = "msg must not be empty"


class AllotropeConversionError(Exception):
    def __init__(self, msg: str) -> None:
        if not msg:
            raise ValueError(_ERROR_MESSAGE)
        super().__init__(msg)


def msg_for_error_on_unrecognized_value(
    key: str, value: Any, valid_values: Optional[Collection[Any]] = None
) -> str:
    msg = f"Unrecognized {key}: '{value}'."
    if valid_values:
        msg += f" Only {sorted(valid_values)} are supported."
    return msg
