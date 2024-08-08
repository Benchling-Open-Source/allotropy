from collections.abc import Collection
from typing import Any


# Unexpected error when reading input data.
class AllotropeParsingError(Exception):
    pass


# Unexpected error when validating output against schema.
class AllotropeValidationError(Exception):
    pass


# Unexpected error when converting allotropy dataclass model to json.
class AllotropeSerializationError(Exception):
    pass


# Expected error caused by bad input data, with a message telling user what the problem is.
class AllotropeConversionError(Exception):
    pass


def msg_for_error_on_unrecognized_value(
    key: str, value: Any, valid_values: Collection[Any] | None = None
) -> str:
    msg = f"Unrecognized {key}: '{value}'."
    if valid_values:
        msg += f" Only {sorted(valid_values)} are supported."
    return msg
