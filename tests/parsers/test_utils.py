from __future__ import annotations

from collections.abc import Mapping
import json
import shutil
import tempfile
from typing import Any, Optional
from unittest import mock

from deepdiff import DeepDiff
import jsonschema
import numpy as np

from allotropy.allotrope.schemas import get_schema
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file, allotrope_model_from_file
from tests.test_id_generator import TestIdGenerator

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


def from_file(test_file: str, vendor: Vendor) -> DictType:
    test_id_generator = TestIdGenerator(vendor)
    # TODO: figure out right invocation magic to patch random_uuid_str() instead.
    with mock.patch("uuid.uuid4", return_value=test_id_generator.generate_id()):
        return allotrope_from_file(test_file, vendor)


def model_from_file(test_file: str, vendor: Vendor) -> Any:
    return allotrope_model_from_file(test_file, vendor)


def _validate_schema(allotrope_dict: DictType, schema_relative_path: str) -> None:
    """Check that the newly created allotrope_dict matches the pre-defined schema from Allotrope."""
    allotrope_schema = get_schema(schema_relative_path)
    jsonschema.validate(
        allotrope_dict,
        allotrope_schema,
        format_checker=jsonschema.validators.Draft202012Validator.FORMAT_CHECKER,
    )


def _get_existing_indent(expected_file: str) -> int:
    with open(expected_file) as f:
        f.readline()
        line = f.readline()
        for i in range(len(line)):
            if not line[i] == " ":
                return i
    raise ValueError("Couldn't determine existing indent")


def _write_actual_to_expected(allotrope_dict: DictType, expected_file: str):
    existing_indent = _get_existing_indent(expected_file)
    with tempfile.NamedTemporaryFile(mode="w+") as tmp:
        try:
            json.dump(allotrope_dict, tmp, indent=existing_indent)
        except Exception as e:
            msg = "Failed to overwrite expected file with actual file"
            raise Exception(msg) from e
        shutil.copy(tmp.name, expected_file)


def _validate_contents(
    allotrope_dict: DictType,
    expected_file: str,
    identifiers_to_exclude: Optional[list[str]],
    write_actual_to_expected_on_fail: bool,  # noqa: FBT001
) -> None:
    """Use the newly created allotrope_dict to validate the contents inside expected_file."""
    with open(expected_file) as f:
        expected_dict = json.load(f)
    expected_replaced = _replace_asm_converter_name_and_version(expected_dict)
    identifiers_to_exclude = identifiers_to_exclude or [
        CALCULATED_DATA_IDENTIFIER,
        DATA_SOURCE_IDENTIFIER,
        MEASUREMENT_IDENTIFIER,
    ]
    # TODO: remove this, param, and above constants once test ids are stable
    identifiers_to_exclude = []
    exclude_regex_paths = [
        fr"\['{exclude_id}'\]" for exclude_id in identifiers_to_exclude
    ]
    ddiff = DeepDiff(
        expected_replaced,
        allotrope_dict,
        exclude_regex_paths=exclude_regex_paths,
        ignore_type_in_groups=[(float, np.float64), (int, np.int64)],
    )

    try:
        assert not ddiff
    except AssertionError:
        if write_actual_to_expected_on_fail:
            _write_actual_to_expected(allotrope_dict, expected_file)
        raise


def generate_allotrope_and_validate(
    test_file: str,
    vendor: Vendor,
    schema_relative_path: str,
    expected_output_file: str,
    identifiers_to_exclude: Optional[list[str]] = None,
    write_actual_to_expected_on_fail: bool = True,  # noqa: FBT001, FBT002
) -> None:
    allotrope_dict = from_file(test_file, vendor)
    _validate_schema(allotrope_dict, schema_relative_path)
    _validate_contents(
        allotrope_dict,
        expected_output_file,
        identifiers_to_exclude,
        write_actual_to_expected_on_fail,
    )

    # Ensure that tests fail if the param is set to True. We never want to commit with a True value.
    assert not write_actual_to_expected_on_fail
