from __future__ import annotations

import copy
from typing import Any

import jsonschema

from allotropy.allotrope.converter import unstructure
from allotropy.allotrope.schemas import get_schema_from_model
from allotropy.exceptions import (
    AllotropeSerializationError,
    AllotropeValidationError,
)

# Override format checker to remove "uri-reference" check, which ASM schemas fail against.
FORMAT_CHECKER = copy.deepcopy(
    jsonschema.validators.Draft202012Validator.FORMAT_CHECKER
)
FORMAT_CHECKER.checkers.pop("uri-reference", None)


def serialize_and_validate_allotrope(model: Any) -> dict[str, Any]:
    try:
        allotrope_dict = unstructure(model)
    except Exception as e:
        msg = f"Failed to serialize allotrope model: {e}"
        raise AllotropeSerializationError(msg) from e

    try:
        allotrope_schema = get_schema_from_model(model)
    except Exception as e:
        msg = f"Failed to retrieve schema for model: {e}"
        raise AllotropeSerializationError(msg) from e

    try:
        jsonschema.validators.Draft202012Validator.check_schema(
            allotrope_schema, format_checker=FORMAT_CHECKER
        )
        validator = jsonschema.validators.Draft202012Validator(allotrope_schema)
        validator.validate(allotrope_dict)
    except Exception as e:
        msg = f"Failed to validate allotrope model against schema: {e}"
        raise AllotropeValidationError(msg) from e
    return allotrope_dict
