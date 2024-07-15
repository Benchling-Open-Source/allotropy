from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any
from unittest import mock

from deepdiff import DeepDiff
import numpy as np

from allotropy.allotrope.converter import structure
from allotropy.constants import ASM_CONVERTER_VERSION, DEFAULT_ENCODING
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file

DictType = Mapping[str, Any]


def _replace_asm_converter_name_and_version(allotrope_dict: DictType) -> DictType:
    new_dict = dict(allotrope_dict)
    for key, value in new_dict.items():
        if key == "data system document":
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
    "group identifier",
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
) -> None:
    expected_replaced = _replace_asm_converter_name_and_version(expected)

    ddiff = DeepDiff(
        expected_replaced,
        actual,
        ignore_type_in_groups=[(float, np.float64)],
        ignore_nan_inequality=True,
    )
    if ddiff:
        msg = f"allotropy output != expected: \n{ddiff.pretty()}"
        raise AssertionError(msg)


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


def from_file(
    test_file: Path | str, vendor: Vendor, encoding: str | None = None
) -> DictType:
    with mock_uuid_generation(vendor.name):
        return allotrope_from_file(str(test_file), vendor, encoding=encoding)


def _write_actual_to_expected(
    allotrope_dict: DictType, expected_file: Path | str
) -> None:
    with tempfile.NamedTemporaryFile(mode="w+", encoding="UTF-8") as tmp:
        json.dump(allotrope_dict, tmp, indent=4, ensure_ascii=False)
        tmp.write("\n")
        tmp.seek(0)
        # Get path to temp file using Pathlib to ensure Windows symbolic link compatibility.
        tmp_path = Path(tmp.name)
        # Ensure this file can be opened as JSON before we copy it
        with tmp_path.open() as tmp_file:
            json.load(tmp_file)
        shutil.copy(tmp_path, expected_file)


def validate_contents(
    allotrope_dict: DictType,
    expected_file: Path | str,
    write_actual_to_expected_on_fail: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """Use the newly created allotrope_dict to validate the contents inside expected_file."""
    # Ensure that allotrope_dict can be written via json.dump()
    with tempfile.TemporaryFile(mode="w+", encoding=DEFAULT_ENCODING) as tmp:
        json.dump(allotrope_dict, tmp, ensure_ascii=False)

    # Ensure that allotrope_dict can be structured back into a python model.
    structure(allotrope_dict)

    # Ensure that all IDs are unique
    _validate_identifiers(allotrope_dict)

    try:
        with open(expected_file, encoding=DEFAULT_ENCODING) as f:
            expected_dict = json.load(f)
        _assert_allotrope_dicts_equal(expected_dict, allotrope_dict)
    except Exception as e:
        if write_actual_to_expected_on_fail:
            _write_actual_to_expected(allotrope_dict, expected_file)
            if isinstance(e, FileNotFoundError):
                msg = f"Missing expected output file '{expected_file}', writing expected output because 'write_actual_to_expected_on_fail=True'"
                raise AssertionError(msg) from e
            if isinstance(e, AssertionError) and "allotropy output != expected:" in str(
                e
            ):
                msg = f"Mismatch between actual and expected for '{expected_file}', writing expected output because 'write_actual_to_expected_on_fail=True'\n\n{e}"
                raise AssertionError(msg) from e
        raise
