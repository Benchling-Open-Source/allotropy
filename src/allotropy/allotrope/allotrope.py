from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Callable, cast

import cattrs
from cattrs.gen import make_dict_unstructure_fn, override
import jsonschema

from allotropy.allotrope.models.cell_culture_analyzer_benchling_2023_09_cell_culture_analyzer import (
    AnalyteDocumentItem,
    MeasurementDocumentItem,
)
from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import (
    ProcessedDataDocumentItem,
)
from allotropy.allotrope.schemas import get_schema_from_model
from allotropy.exceptions import AllotropeConversionError

# TODO: gather exceptions when parsing models from schema and publish them in model
SPECIAL_KEYS = {
    "manifest": "$asm.manifest",
    "field_asm_manifest": "$asm.manifest",
    "cube_structure": "cube-structure",
    "field_componentDatatype": "@componentDatatype",
    "field_asm_fill_value": "$asm.fill-value",
    "field_type": "@type",
    "field_index": "@index",
    "scan_position_setting__plate_reader_": "scan position setting (plate reader)",
    "detector_distance_setting__plate_reader_": "detector distance setting (plate reader)",
    "cell_type__cell_counter_": "cell type (cell counter)",
    "dead_cell_density__cell_counter_": "dead cell density (cell counter)",
    "average_dead_cell_diameter__cell_counter_": "average dead cell diameter (cell counter)",
    "viability__cell_counter_": "viability (cell counter)",
    "total_cell_density__cell_counter_": "total cell density (cell counter)",
    "viable_cell_density__cell_counter_": "viable cell density (cell counter)",
    "average_live_cell_diameter__cell_counter_": "average live cell diameter (cell counter)",
    "average_total_cell_diameter__cell_counter_": "average total cell diameter (cell counter)",
    "total_cell_diameter_distribution__cell_counter_": "total cell diameter distribution (cell counter)",
    "viable_cell_count__cell_counter_": "viable cell count (cell counter)",
    "total_cell_count__cell_counter_": "total cell count (cell counter)",
    "pco2": "pCO2",
    "co2_saturation": "CO2 saturation",
    "po2": "pO2",
    "o2_saturation": "O2 saturation",
}


CELL_CULTURE_NULLABLE_VALUE_CLASSES: dict[Any, set[str]] = {
    MeasurementDocumentItem: {
        "pco2",
        "co2_saturation",
        "po2",
        "o2_saturation",
        "optical_density",
        "pH",
        "osmolality",
        "viability__cell_counter_",
        "total_cell_density__cell_counter_",
        "viable_cell_density__cell_counter_",
        "average_live_cell_diameter__cell_counter_",
        "average_total_cell_diameter__cell_counter_",
        "total_cell_diameter_distribution__cell_counter_",
        "viable_cell_count__cell_counter_",
        "total_cell_count__cell_counter_",
    },
    AnalyteDocumentItem: {"molar_concentration"},
}

QPCR_NULLABLE_VALUE_CLASSES: dict[Any, set[str]] = {
    ProcessedDataDocumentItem: {"cycle_threshold_result"}
}

EMPTY_VALUE_CLASS_AND_FIELD = {
    **CELL_CULTURE_NULLABLE_VALUE_CLASSES,
    **QPCR_NULLABLE_VALUE_CLASSES,
}


def should_allow_empty_value_field(cls: Any, key: str) -> bool:
    return key in EMPTY_VALUE_CLASS_AND_FIELD.get(cls, set())


def get_key(key: str) -> str:
    return SPECIAL_KEYS.get(key, key.replace("_", " "))


def serialize_allotrope(model: Any) -> dict[str, Any]:
    converter = cattrs.Converter()

    # Default check for omitting values skips if value is None
    def should_omit(_: str, v: Any) -> bool:
        return v is None

    # Special should_omit check for allowing an empty value for 'value' keys, controlled by should_allow_empty_value_field
    def should_omit_allow_empty_value_field(k: str, v: Any) -> bool:
        return v is None and k != "value"

    unstructure_fn_cache = {}

    def unstructure_dataclass_fn(
        cls: Any, should_omit: Callable[[str, Any], bool] = should_omit
    ) -> Callable[[Any], dict[str, Any]]:
        def unstructure(obj: Any) -> Any:
            # Break out of dataclass recursion by calling back to converter.unstructure
            if not is_dataclass(obj):
                return converter.unstructure(obj)

            return {
                get_key(k): v
                for k, v in make_unstructure_fn(type(obj))(obj).items()
                if not should_omit(k, v)
            }

        # This custom unstructure function overrides the unstruct_hook when we should should_allow_empty_value_field.
        # We need to do this at this level because we need to know both the parent class and the field name at the
        # same time.
        def make_unstructure_fn(subcls: Any) -> Callable[[Any], dict[str, Any]]:
            if (cls, subcls) not in unstructure_fn_cache:
                unstructure_fn_cache[(cls, subcls)] = make_dict_unstructure_fn(
                    subcls,
                    converter,
                    **{
                        a.name: override(
                            unstruct_hook=unstructure_dataclass_fn(
                                subcls, should_omit_allow_empty_value_field
                            )
                            if should_allow_empty_value_field(cls, a.name)
                            else None
                        )
                        for a in fields(cls)
                    },
                )
            return unstructure_fn_cache[(cls, subcls)]

        return unstructure

    converter.register_unstructure_hook_factory(is_dataclass, unstructure_dataclass_fn)
    result = converter.unstructure(model)
    return cast(dict[str, Any], result)


def serialize_and_validate_allotrope(model: Any) -> dict[str, Any]:
    try:
        allotrope_dict = serialize_allotrope(model)
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
