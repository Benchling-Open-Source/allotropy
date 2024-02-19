from __future__ import annotations

from collections.abc import Mapping
import json
import tempfile
from typing import Any, Optional

from deepdiff import DeepDiff
import numpy as np

from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.parser_factory import VendorType
from allotropy.to_allotrope import allotrope_from_file

CALCULATED_DATA_IDENTIFIER = "calculated data identifier"
DATA_SOURCE_IDENTIFIER = "data source identifier"
MEASUREMENT_IDENTIFIER = "measurement identifier"

DictType = Mapping[str, Any]


def _replace_asm_converter_name_and_version(allotrope_dict: DictType) -> DictType:
    new_dict = dict(allotrope_dict)
    for key, value in new_dict.items():
        if key == "data system document":
            value["ASM converter name"] = ASM_CONVERTER_NAME
            value["ASM converter version"] = ASM_CONVERTER_VERSION
        if isinstance(value, dict):
            _replace_asm_converter_name_and_version(value)

    return new_dict


def _assert_allotrope_dicts_equal(
    expected: DictType,
    actual: DictType,
    identifiers_to_exclude: Optional[list[str]] = None,
) -> None:
    expected_replaced = _replace_asm_converter_name_and_version(expected)

    identifiers_to_exclude = identifiers_to_exclude or [
        CALCULATED_DATA_IDENTIFIER,
        DATA_SOURCE_IDENTIFIER,
        MEASUREMENT_IDENTIFIER,
    ]
    exclude_regex_paths = [
        fr"\['{exclude_id}'\]" for exclude_id in identifiers_to_exclude
    ]
    ddiff = DeepDiff(
        expected_replaced,
        actual,
        exclude_regex_paths=exclude_regex_paths,
        ignore_type_in_groups=[(float, np.float64), (int, np.int64)],
    )
    assert not ddiff


def from_file(test_file: str, vendor_type: VendorType) -> DictType:
    return allotrope_from_file(test_file, vendor_type)


def validate_contents(
    allotrope_dict: DictType,
    expected_file: str,
    identifiers_to_exclude: Optional[list[str]] = None,
) -> None:
    """Use the newly created allotrope_dict to validate the contents inside expected_file."""
    with open(expected_file) as f:
        expected_dict = json.load(f)
    _assert_allotrope_dicts_equal(
        expected_dict, allotrope_dict, identifiers_to_exclude=identifiers_to_exclude
    )

    # Ensure that allotrope_dict can be written via json.dump()
    with tempfile.TemporaryFile(mode="w+") as tmp:
        json.dump(allotrope_dict, tmp)
