from __future__ import annotations

from typing import Any

import jsonschema

from allotropy.allotrope.converter import unstructure
from allotropy.allotrope.schemas import get_schema_from_model
from allotropy.exceptions import AllotropeConversionError


def serialize_and_validate_allotrope(model: Any) -> dict[str, Any]:
    try:
        allotrope_dict = unstructure(model)
    except Exception as e:
        msg = f"Failed to serialize allotrope model: {e}"
        raise AllotropeConversionError(msg) from e

    try:
        allotrope_schema = get_schema_from_model(model)
    except Exception as e:
        msg = f"Failed to retrieve schema for model: {e}"
        raise AllotropeConversionError(msg) from e

    try:
        jsonschema.validate(
            allotrope_dict,
            allotrope_schema,
            cls=jsonschema.validators.Draft202012Validator,
        )
    except Exception as e:
        msg = f"Failed to validate allotrope model against schema: {e}"
        raise AllotropeConversionError(msg) from e
    return allotrope_dict
