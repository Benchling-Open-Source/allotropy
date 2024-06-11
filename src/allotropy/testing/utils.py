from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
import json
import shutil
import tempfile
from typing import Any
from unittest import mock

from deepdiff import DeepDiff
import numpy as np

from allotropy.allotrope.converter import structure
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file

DictType = Mapping[str, Any]


def _replace_asm_converter_name_and_version(allotrope_dict: DictType) -> DictType:
    new_dict = dict(allotrope_dict)
    for key, value in new_dict.items():
        if key == "data system document":
            # TODO: Commenting this out until BNCH-93726 is completed.
            # value["ASM converter name"] = ASM_CONVERTER_NAME
            value["ASM converter version"] = ASM_CONVERTER_VERSION
        if isinstance(value, dict):
            _replace_asm_converter_name_and_version(value)

    return new_dict


# List of keys in ASM with "identifier" that do not need to be unique.
# Currently, only "measurement identifier" and "calculated data document" identifier should be unique.
# However, it is better to have positive exceptions, so we don't accidentally miss a newly added unique identifier.
NON_UNIQUE_IDENTIFIERS = {
    "analytical method identifier",
    "assay bead identifier",
    "batch identifier",
    "data source identifier",
    "device identifier",
    "experimental data identifier",
    "location identifier",
    "measurement method identifier",
    "sample identifier",
    "well location identifier",
    "well plate identifier",
}


def _is_unique_identifier(key: str) -> bool:
    return "identifier" in key and key not in NON_UNIQUE_IDENTIFIERS


def _get_all_identifiers(asm: DictType) -> dict[str, list[str]]:
    all_identifiers = defaultdict(list)
    for key, value in asm.items():
        if isinstance(value, dict):
            for subkey, subvalue in _get_all_identifiers(value).items():
                all_identifiers[subkey].extend(subvalue)
        elif isinstance(value, list):
            for v in value:
                if isinstance(v, dict):
                    for subkey, subvalue in _get_all_identifiers(v).items():
                        all_identifiers[subkey].extend(subvalue)
        elif _is_unique_identifier(key):
            all_identifiers[key].append(value)
    return {key: list(value) for key, value in all_identifiers.items()}


def _validate_identifiers(asm: DictType) -> None:
    for key, value in _get_all_identifiers(asm).items():
        if len(value) != len(set(value)):
            non_unique = [id_ for id_ in set(value) if value.count(id_) > 1]
            msg = f"Detected non-unique identifiers for key '{key}'. If this key should allow repeat values, add to NON_UNIQUE_IDENTIFIERS. Identifiers: {non_unique}"
            raise AssertionError(msg)


def _assert_allotrope_dicts_equal(
    expected: DictType,
    actual: DictType,
    print_verbose_deep_diff: bool = False,  # noqa: FBT001, FBT002
) -> None:
    expected_replaced = _replace_asm_converter_name_and_version(expected)

    ddiff = DeepDiff(
        expected_replaced,
        actual,
        ignore_type_in_groups=[(float, np.float64)],
        ignore_nan_inequality=True,
    )
    if print_verbose_deep_diff:
        print(ddiff)  # noqa: T201
    assert not ddiff  # noqa: S101


class TestIdGenerator:
    next_id: int
    prefix: str | None

    def __init__(self, prefix: str | None) -> None:
        self.prefix = f"{prefix}_" if prefix else ""
        self.next_id = 0

    def generate_id(self) -> str:
        current_id = f"{self.prefix}TEST_ID_{self.next_id}"
        self.next_id += 1
        return current_id


@contextmanager
def mock_uuid_generation(prefix: str | None) -> Iterator[None]:
    with mock.patch(
        "allotropy.parsers.utils.uuids._IdGeneratorFactory.get_id_generator",
        return_value=TestIdGenerator(prefix),
    ):
        yield


def from_file(test_file: str, vendor: Vendor, encoding: str | None = None) -> DictType:
    with mock_uuid_generation(vendor.name):
        return allotrope_from_file(test_file, vendor, encoding=encoding)


def _write_actual_to_expected(allotrope_dict: DictType, expected_file: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w+") as tmp:
        json.dump(allotrope_dict, tmp, indent=4, ensure_ascii=False)
        tmp.write("\n")
        tmp.seek(0)
        json.load(tmp)  # Ensure this file can be opened as JSON before we copy it
        shutil.copy(tmp.name, expected_file)


def validate_contents(
    allotrope_dict: DictType,
    expected_file: str,
    write_actual_to_expected_on_fail: bool = False,  # noqa: FBT001, FBT002
    print_verbose_deep_diff: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """Use the newly created allotrope_dict to validate the contents inside expected_file."""
    with open(expected_file) as f:
        expected_dict = json.load(f)

    # Ensure that allotrope_dict can be written via json.dump()
    with tempfile.TemporaryFile(mode="w+") as tmp:
        json.dump(allotrope_dict, tmp)

    # Ensure that allotrope_dict can be structured back into a python model.
    structure(allotrope_dict)

    # Ensure that all IDs are unique
    _validate_identifiers(allotrope_dict)

    try:
        _assert_allotrope_dicts_equal(
            expected_dict, allotrope_dict, print_verbose_deep_diff
        )
    except Exception:
        if write_actual_to_expected_on_fail:
            _write_actual_to_expected(allotrope_dict, expected_file)
        raise
