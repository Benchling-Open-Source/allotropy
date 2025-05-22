from __future__ import annotations

import builtins
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, field, fields, is_dataclass, make_dataclass, MISSING
from enum import Enum
from types import GenericAlias, UnionType
from typing import (
    Any,
    cast,
    get_args,
    get_origin,
    TypeVar,
    Union,
)

from cattrs import Converter
from cattrs.errors import ClassValidationError
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn, override
import numpy as np

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import (
    ProcessedDataDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    TDimensionArray,
    TFunction,
    TMeasureArray,
)
from allotropy.allotrope.models.shared.definitions.units import HasUnit
from allotropy.allotrope.schema_parser.path_util import get_model_class_from_schema

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
    "cycle_threshold_value_setting__qPCR_": "cycle threshold value setting (qPCR)",
    "genotyping_qPCR_method_setting__qPCR_": "genotyping qPCR method setting (qPCR)",
    "cycle_threshold_result__qPCR_": "cycle threshold result (qPCR)",
    "autosampler_injection_volume_setting__chromatography_": "autosampler injection volume setting (chromatography)",
    "capacity_factor__chromatography_": "capacity factor (chromatography)",
    "peak_selectivity__chromatography_": "peak selectivity (chromatography)",
    "peak_width_at_4_4___of_height": "peak width at 4.4 % of height",
    "peak_width_at_13_4___of_height": "peak width at 13.4 % of height",
    "peak_width_at_32_4___of_height": "peak width at 32.4 % of height",
    "peak_width_at_60_7___of_height": "peak width at 60.7 % of height",
    "peak_width_at_5___of_height": "peak width at 5 % of height",
    "peak_width_at_10___of_height": "peak width at 10 % of height",
    "statistical_skew__chromatography_": "statistical skew (chromatography)",
    "asymmetry_factor_measured_at_5___height": "asymmetry factor measured at 5 % height",
    "asymmetry_factor_measured_at_10___height": "asymmetry factor measured at 10 % height",
    "asymmetry_factor_squared_measured_at_10___height": "asymmetry factor squared measured at 10 % height",
    "asymmetry_factor_squared_measured_at_4_4___height": "asymmetry factor squared measured at 4.4 % height",
    "asymmetry_factor_measured_at_4_4___height": "asymmetry factor measured at 4.4 % height",
    "number_of_theoretical_plates__chromatography_": "number of theoretical plates (chromatography)",
    "number_of_theoretical_plates_measured_at_60_7___of_peak_height": "number of theoretical plates measured at 60.7 % of peak height",
    "number_of_theoretical_plates_measured_at_32_4___of_peak_height": "number of theoretical plates measured at 32.4 % of peak height",
    "number_of_theoretical_plates_measured_at_13_4___of_peak_height": "number of theoretical plates measured at 13.4 % of peak height",
    "number_of_theoretical_plates_measured_at_4_4___of_peak_height": "number of theoretical plates measured at 4.4 % of peak height",
    "number_of_theoretical_plates_by_peak_width_at_half_height__JP14_": "number of theoretical plates by peak width at half height (JP14)",
    "confidence_interval__95__": "confidence interval (95%)",
    "co2_saturation": "CO2 saturation",
    "o2_saturation": "O2 saturation",
    "pco2": "pCO2",
    "po2": "pO2",
}
SPECIAL_KEYS_INVERSE: dict[str, str] = dict(
    cast(tuple[str, str], reversed(item)) for item in SPECIAL_KEYS.items()
)


DICT_KEY_TO_MODEL_KEY_REPLACEMENTS = {
    ".": "_POINT_",
    "-": "_DASH_",
    "°": "_DEG_",
    "/": "_SLASH_",
    "\\": "_BSLASH_",
    "(": "_OPAREN_",
    ")": "_CPAREN_",
    "%": "_PERCENT_",
    ":": "_COLON_",
    "#": "_NUMBER_",
    "[": "_OBRACKET_",
    "]": "_CBRACKET_",
    "~": "_TILDE_",
    "?": "_QMARK_",
    # NOTE: this MUST be at the end, or it will break other key replacements.
    " ": "_",
}


PRIMITIVE_TYPES = (
    bool,
    int,
    float,
    str,
    type(None),
    InvalidJsonFloat,
    np.float64,
    np.int64,
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

    model.custom_information_document = custom_info_doc  # type: ignore
    return model


def _convert_model_key_to_dict_key(key: str) -> str:
    key = SPECIAL_KEYS.get(key, key)
    if key.startswith("___") and key[3].isdigit():
        key = key[3:]
    for dict_val, model_val in DICT_KEY_TO_MODEL_KEY_REPLACEMENTS.items():
        key = key.replace(model_val, dict_val)
    return key


def _convert_dict_to_model_key(key: str) -> str:
    key = SPECIAL_KEYS_INVERSE.get(key, key)
    if key[0].isdigit():
        key = f"___{key}"
    for dict_val, model_val in DICT_KEY_TO_MODEL_KEY_REPLACEMENTS.items():
        key = key.replace(dict_val, model_val)
    return key


def _validate_structuring(val: Any, model: Any) -> None:
    """Validate that all keys in val are stored in model."""
    if isinstance(val, list):
        if not isinstance(model, list):
            raise AssertionError()
        for list_value, model_list_value in zip(val, model, strict=True):
            _validate_structuring(list_value, model_list_value)
    if not isinstance(val, dict):
        return

    for key, value in val.items():
        model_key = _convert_dict_to_model_key(key)
        # If the key is unit, and this is a unit model, ensure the unit is correct.
        if key == "unit" and isinstance(model, HasUnit):
            unit_field = next(field for field in fields(model) if field.name == "unit")
            if not value == unit_field.default:
                raise AssertionError()
        # If the value itself is None, just assert that the key is in the model.
        if value is None:
            if not hasattr(model, model_key):
                raise AssertionError()
            continue

        model_val = getattr(model, model_key, None)
        if model_val is None:
            raise AssertionError()

        _validate_structuring(value, model_val)


def register_data_cube_hooks(converter: Converter) -> None:
    def structure_dimension_array(val: Any, _: Any) -> TDimensionArray | TFunction:
        if isinstance(val, list):
            return val
        return converter.structure(val, TFunction)

    converter.register_structure_hook(
        TDimensionArray | TFunction, structure_dimension_array
    )
    converter.register_structure_hook(TMeasureArray, lambda val, _: val)


# TODO: this code is copied from cattrs 24.1.0. We currently pin to 23.1.2 because some other libraries that
# allotropy is currently used with pin cattrs (i.e. ddtrace). When possible, upgrade to cattrs>=24.1.0 and
# import is_sequence from cattrs.cols
def is_subclass(obj: type, bases: builtins._ClassInfo) -> bool:
    """A safe version of issubclass (won't raise)."""
    try:
        return issubclass(obj, bases)
    except TypeError:
        return False


def is_sequence(type_: Any) -> bool:
    origin = getattr(type_, "__origin__", None)
    return type_ in (list, tuple) or (
        type_.__class__ in (GenericAlias, type)
        and origin
        and (origin not in (Union, tuple) and is_subclass(origin, Sequence))
        or (origin is tuple and type_.__args__[1] is ...)
    )


def register_dataclass_union_hooks(converter: Converter) -> None:
    # Handles any union of dataclass, lists of dataclasses, and primitive values.
    # First checks if the value is a list, and if so tries to parse with any of the list types.
    # Then checks if the value is a primitive value or None, and if so returns that.
    # Then tries structuring with each specified dataclass, if any.
    def _is_valid(arg: Any) -> bool:
        if is_sequence(arg):
            return all(is_dataclass(sub) for sub in arg.__args__)
        if is_dataclass(arg):
            return True
        if arg in PRIMITIVE_TYPES:
            return True
        return False

    def is_dataclass_union(val: Any) -> bool:
        if get_origin(val) not in (Union, UnionType):
            return False
        args = set(get_args(val))
        return all(_is_valid(arg) for arg in args)

    def dataclass_union_structure_fn(
        cls: Any,
    ) -> Callable[[dict[str, Any] | str | None, Any], Any | None]:
        def structure_item(val: dict[str, Any] | str | None, _: Any) -> Any | None:
            if isinstance(val, list):
                valid_models = []
                for subcls in get_args(cls):
                    if not is_sequence(subcls):
                        continue
                    # I don't think this should be possible, but check and raise a readable error just in case.
                    if len(subcls.__args__) > 1:
                        msg = (
                            f"Encountered a list type with more than one arg: {subcls}!"
                        )
                        raise AssertionError(msg)
                    try:
                        valid_models.append(
                            [converter.structure(v, subcls.__args__[0]) for v in val]
                        )
                    except (ClassValidationError, TypeError):
                        pass

                if len(valid_models) == 1:
                    return valid_models[0]
                elif len(valid_models) > 1:
                    for model in valid_models:
                        try:
                            _validate_structuring(val, model)
                            return model
                        except AssertionError:
                            pass

            if type(val) in PRIMITIVE_TYPES:
                return val
            valid_models = []
            for subcls in get_args(cls):
                if not is_dataclass(subcls):
                    continue
                try:
                    valid_models.append(converter.structure(val, subcls))
                except ClassValidationError:
                    pass

            if len(valid_models) == 1:
                return valid_models[0]
            elif len(valid_models) > 1:
                for model in valid_models:
                    try:
                        _validate_structuring(val, model)
                        return model
                    except AssertionError:
                        pass

            msg = f"Failed to structure value {val} with type {cls}"
            raise ValueError(msg)

        return structure_item

    converter.register_structure_hook_factory(
        is_dataclass_union, dataclass_union_structure_fn
    )


def structure_custom_information_document(val: dict[str, Any], name: str) -> Any:
    structured_dict = {}
    for key, value in val.items():
        structured_value = value
        if isinstance(value, list):
            structured_value = [
                structure_custom_information_document(v, key)
                if isinstance(v, dict)
                else value
                if isinstance(v, list)
                else v
                for v in value
            ]
        elif isinstance(value, dict):
            structured_value = structure_custom_information_document(value, key)
        structured_dict[_convert_dict_to_model_key(key)] = structured_value

    name = name.title().replace(" ", "")
    return make_dataclass(
        name, ((k, type(v), field(default=None)) for k, v in structured_dict.items())
    )(**structured_dict)


def _create_should_omit_function(
    cls: Any, parent_cls: Any | None = None, field_name: str | None = None
) -> Callable[[str, Any], bool]:
    required_keys = {a.name for a in fields(cls) if a.default == MISSING}

    def should_omit(k: str, v: Any) -> bool:
        if k in required_keys:
            return False
        if field_name in EMPTY_VALUE_CLASS_AND_FIELD.get(parent_cls, set()):
            return v is None and k != "value"
        return v is None

    return should_omit


def _unstructure_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def unstructure_custom_information_document(model: Any) -> dict[str, Any]:
    should_omit = _create_should_omit_function(model)

    def dict_factory(kv_pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        return {
            _convert_model_key_to_dict_key(key): _unstructure_value(value)
            for key, value in kv_pairs
            if not should_omit(key, value)
        }

    return asdict(model, dict_factory=dict_factory)


def register_dataclass_hooks(converter: Converter) -> None:
    def dataclass_structure_fn(cls: Any) -> Callable[[Any, Any], Any | None]:
        field_name_overrides = {
            a.name: override(rename=_convert_model_key_to_dict_key(a.name))
            for a in fields(cls)
        }
        structure_fn = make_dict_structure_fn(
            cls,
            converter,
            # mypy does not recognize that unpacking a dictionary is specifying kwargs
            **field_name_overrides,  # type: ignore[arg-type]
        )

        def structure_item(val: Any, _: Any) -> Any | None:
            if val is None:
                return None
            structured = structure_fn(val, _)
            # NOTE: this handles custom implementation of custom info document, not the ASM version that came
            # later. The ASM version will always be a list, so we can differentiate using that.
            if (
                isinstance(val, dict)
                and "custom information document" in val
                and not isinstance(val["custom information document"], list)
            ):
                structured.custom_information_document = (
                    structure_custom_information_document(
                        val["custom information document"],
                        "custom information document",
                    )
                )
            return structured

        return structure_item

    converter.register_structure_hook_factory(is_dataclass, dataclass_structure_fn)


QPCR_NULLABLE_VALUE_CLASSES: dict[Any, set[str]] = {
    ProcessedDataDocumentItem: {"cycle_threshold_result"}
}

EMPTY_VALUE_CLASS_AND_FIELD = {
    **QPCR_NULLABLE_VALUE_CLASSES,
}


def register_unstructure_hooks(converter: Converter) -> None:
    unstructure_fn_cache = {}

    def unstructure_dataclass_fn(
        cls: Any, parent_cls: Any | None = None, field_name: str | None = None
    ) -> Callable[[Any], dict[str, Any]]:
        should_omit = _create_should_omit_function(cls, parent_cls, field_name)

        def unstructure(obj: Any) -> Any:
            # Break out of dataclass recursion by calling back to converter.unstructure
            if not is_dataclass(obj):
                return converter.unstructure(obj)

            dataclass_dict = {
                _convert_model_key_to_dict_key(k): v
                for k, v in make_unstructure_fn(type(obj))(obj).items()
                if not should_omit(k, v)
            }
            # NOTE: this handles custom implementation of custom info document, not the ASM version that came
            # later. The ASM version will always be a list, so we can differentiate using that.
            if hasattr(obj, "custom_information_document") and not isinstance(
                obj.custom_information_document, list
            ):
                dataclass_dict[
                    "custom information document"
                ] = unstructure_custom_information_document(
                    obj.custom_information_document
                )
            return dataclass_dict

        # This custom unstructure function overrides the unstruct_hook. We need to do this at this level
        # because we need to know both the parent class and the field name at the same time to create the
        # should_omit function.
        def make_unstructure_fn(subcls: Any) -> Callable[[Any], dict[str, Any]]:
            if (cls, subcls) not in unstructure_fn_cache:
                field_name_overrides = {
                    a.name: override(
                        unstruct_hook=unstructure_dataclass_fn(subcls, cls, a.name)
                    )
                    for a in fields(cls)
                }
                unstructure_fn_cache[(cls, subcls)] = make_dict_unstructure_fn(
                    subcls,
                    converter,
                    # mypy does not recognize that unpacking a dictionary is specifying kwargs
                    **field_name_overrides,  # type: ignore[arg-type]
                )
            return unstructure_fn_cache[(cls, subcls)]

        return unstructure

    converter.register_unstructure_hook_factory(is_dataclass, unstructure_dataclass_fn)


def setup_converter() -> Converter:
    converter = Converter()
    register_data_cube_hooks(converter)
    register_dataclass_union_hooks(converter)
    register_dataclass_hooks(converter)
    register_unstructure_hooks(converter)
    return converter


CONVERTER = setup_converter()


def unstructure(model: Any) -> dict[str, Any]:
    return cast(dict[str, Any], CONVERTER.unstructure(model))


def structure(asm: Mapping[str, Any], model_class: Any | None = None) -> Any:
    model_class = model_class or get_model_class_from_schema(asm)
    return CONVERTER.structure(asm, model_class)
