from __future__ import annotations

from collections.abc import Mapping
import json
import shutil
import tempfile
from typing import Any, Optional
from unittest import mock

from deepdiff import DeepDiff
import numpy as np

from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.parser_factory import Vendor
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
    # TODO: remove identifiers_to_exclude once test ids are stable
    identifiers_to_exclude = []
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


class TestIdGenerator:
    vendor: Vendor
    next_id: int

    def __init__(self, vendor: Vendor) -> None:
        self.vendor = vendor
        self.next_id = 0

    def generate_id(self) -> str:
        current_id = f"{self.vendor.name}_TEST_ID_{self.next_id}"
        self.next_id += 1
        return current_id


def from_file(test_file: str, vendor: Vendor) -> DictType:
    with mock.patch(
        "allotropy.parsers.vendor_parser.VendorParser.random_uuid_str",
        return_value=TestIdGenerator(vendor).generate_id(),
    ):
        return allotrope_from_file(test_file, vendor)


def _get_existing_indent(expected_file: str) -> int:
    with open(expected_file) as f:
        f.readline()
        line = f.readline()
        for i in range(len(line)):
            if not line[i] == " ":
                return i
    msg = "Couldn't determine existing indent"
    raise ValueError(msg)


def _write_actual_to_expected(allotrope_dict: DictType, expected_file: str) -> None:
    existing_indent = _get_existing_indent(expected_file)
    with tempfile.NamedTemporaryFile(mode="w+") as tmp:
        json.dump(allotrope_dict, tmp, indent=existing_indent)
        tmp.seek(0)
        json.load(tmp)  # Ensure this file can be opened as JSON before we copy it
        shutil.copy(tmp.name, expected_file)


def validate_contents(
    allotrope_dict: DictType,
    expected_file: str,
    identifiers_to_exclude: Optional[list[str]] = None,
    write_actual_to_expected_on_fail: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """Use the newly created allotrope_dict to validate the contents inside expected_file."""
    with open(expected_file) as f:
        expected_dict = json.load(f)

    try:
        _assert_allotrope_dicts_equal(
            expected_dict, allotrope_dict, identifiers_to_exclude=identifiers_to_exclude
        )
    except:  # noqa: E722
        if write_actual_to_expected_on_fail:
            _write_actual_to_expected(allotrope_dict, expected_file)
        raise

    # Ensure that tests fail if the param is set to True. We never want to commit with a True value.
    assert not write_actual_to_expected_on_fail
