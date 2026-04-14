from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, field, is_dataclass, make_dataclass
import keyword
from typing import Any, cast, TypeVar

from allotropy.allotrope.path_util import get_model_class_from_schema
from allotropy.schema_gen.serializer import (
    DICT_KEY_TO_MODEL_KEY_REPLACEMENTS,
    from_dict,
    to_dict,
)

ModelClass = TypeVar("ModelClass")


def add_custom_information_document(
    model: ModelClass, custom_info_doc: Any
) -> ModelClass:
    if not custom_info_doc:
        return model

    # Convert to a dictionary first, so we can clean up values.
    if is_dataclass(custom_info_doc):
        custom_info_dict = asdict(custom_info_doc)
    elif isinstance(custom_info_doc, dict):
        custom_info_dict = custom_info_doc
    else:
        msg = f"Invalid custom_info_doc: {custom_info_doc}"
        raise ValueError(msg)

    # Remove None and {"value": None, "unit"...} values
    cleaned_dict = {}
    for key, value in custom_info_dict.items():
        if value is None:
            continue
        if isinstance(value, dict) and "value" in value and value["value"] is None:
            continue
        cleaned_dict[key] = value

    # If dict is empty after cleaning, do not attach.
    if not cleaned_dict:
        return model

    custom_info_doc = structure_custom_information_document(
        cleaned_dict, "custom information document"
    )

    try:
        model.custom_information_document = custom_info_doc  # type: ignore
    except AttributeError:
        # Frozen dataclasses block __setattr__; bypass with object.__setattr__
        object.__setattr__(model, "custom_information_document", custom_info_doc)
    return model


def _convert_dict_to_model_key(key: str) -> str:
    if keyword.iskeyword(key):
        key = f"_KW{key}"
    if key[0].isdigit():
        key = f"___{key}"
    for dict_val, model_val in DICT_KEY_TO_MODEL_KEY_REPLACEMENTS.items():
        key = key.replace(dict_val, model_val)
    return key


def structure_custom_information_document(val: dict[str, Any], name: str) -> Any:
    structured_dict = {}
    for key, value in val.items():
        structured_value = value
        if isinstance(value, list):
            structured_value = [
                (
                    structure_custom_information_document(v, key)
                    if isinstance(v, dict)
                    else value
                    if isinstance(v, list)
                    else v
                )
                for v in value
            ]
        elif isinstance(value, dict):
            structured_value = structure_custom_information_document(value, key)
        structured_dict[_convert_dict_to_model_key(key)] = structured_value

    name = name.title().replace(" ", "")
    return make_dataclass(
        name, ((k, type(v), field(default=None)) for k, v in structured_dict.items())
    )(**structured_dict)


def unstructure(model: Any) -> dict[str, Any]:
    return cast(dict[str, Any], to_dict(model))


def structure(asm: Mapping[str, Any], model_class: Any | None = None) -> Any:
    model_class = model_class or get_model_class_from_schema(asm)
    return from_dict(asm, model_class)
