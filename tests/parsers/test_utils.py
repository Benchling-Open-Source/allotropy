# mypy: disallow_any_generics = False

import json
from typing import Any

from deepdiff import DeepDiff
import jsonschema
import numpy as np
import pandas as pd

from allotropy.allotrope.schemas import get_schema
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.parser_factory import VendorType
from allotropy.to_allotrope import allotrope_from_file


def replace_asm_converter_name_and_version(allotrope_dict: dict) -> None:
    for key, value in allotrope_dict.items():
        if key == "data system document":
            value["ASM converter name"] = ASM_CONVERTER_NAME
            value["ASM converter version"] = ASM_CONVERTER_VERSION
        if isinstance(value, dict):
            replace_asm_converter_name_and_version(value)


def assert_allotrope_dicts_equal(expected: dict, actual: dict) -> None:
    replace_asm_converter_name_and_version(expected)
    exclude_regex = [
        r"\['measurement identifier'\]",
        r"\['data source identifier'\]",
        r"\['calculated data identifier'\]",
    ]
    # Uncomment for more info
    # print(DeepDiff(expected, actual, exclude_regex_paths=exclude_regex))
    assert not DeepDiff(
        expected,
        actual,
        exclude_regex_paths=exclude_regex,
        ignore_type_in_groups=[(float, np.float64)],
    )


def from_file(test_file: str, vendor_type: VendorType) -> dict[str, Any]:
    return allotrope_from_file(test_file, vendor_type)


def validate_schema(allotrope_dict: dict[str, Any], schema_relative_path: str) -> None:
    """Check that the newly created allotrope_dict matches the pre-defined schema from Allotrope."""
    allotrope_schema = get_schema(schema_relative_path)
    jsonschema.validate(
        allotrope_dict,
        allotrope_schema,
        format_checker=jsonschema.validators.Draft202012Validator.FORMAT_CHECKER,
    )


def validate_contents(allotrope_dict: dict[str, Any], expected_file: str) -> None:
    """Use the newly created allotrope_dict to validate the contents inside expected_file."""
    with open(expected_file) as f:
        expected_dict = json.load(f)
        assert_allotrope_dicts_equal(expected_dict, allotrope_dict)


def build_series(elements: list[tuple]) -> pd.Series:
    index, data = list(zip(*elements))
    # pd.Series has a Generic.
    return pd.Series(data=data, index=index)  # type: ignore[no-any-return]
