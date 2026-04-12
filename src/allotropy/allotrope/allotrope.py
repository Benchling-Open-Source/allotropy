from __future__ import annotations

from typing import Any

from allotropy.allotrope.converter import unstructure
from allotropy.allotrope.schemas import validate_asm_schema
from allotropy.exceptions import AllotropeSerializationError


def serialize_and_validate_allotrope(model: Any) -> dict[str, Any]:
    try:
        allotrope_dict = unstructure(model)
    except Exception as e:
        msg = f"Failed to serialize allotrope model: {e}"
        raise AllotropeSerializationError(msg) from e

    validate_asm_schema(allotrope_dict)

    return allotrope_dict
