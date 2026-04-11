from __future__ import annotations

from typing import Any

from allotropy.allotrope.converter import is_v2_model, unstructure, unstructure_v2
from allotropy.allotrope.schemas import validate_asm_schema
from allotropy.exceptions import AllotropeSerializationError


def serialize_and_validate_allotrope(model: Any) -> dict[str, Any]:
    try:
        if is_v2_model(model):
            allotrope_dict = unstructure_v2(model)
        else:
            allotrope_dict = unstructure(model)
    except Exception as e:
        msg = f"Failed to serialize allotrope model: {e}"
        raise AllotropeSerializationError(msg) from e

    validate_asm_schema(allotrope_dict)

    return allotrope_dict


def serialize_and_validate_allotrope_v2(model: Any) -> dict[str, Any]:
    """V2 entrypoint — same signature as serialize_and_validate_allotrope.

    Uses json_name metadata on v2 dataclass fields for serialization
    instead of the cattrs-based converter used by v1 models.
    """
    try:
        allotrope_dict = unstructure_v2(model)
    except Exception as e:
        msg = f"Failed to serialize allotrope model: {e}"
        raise AllotropeSerializationError(msg) from e

    validate_asm_schema(allotrope_dict)

    return allotrope_dict
