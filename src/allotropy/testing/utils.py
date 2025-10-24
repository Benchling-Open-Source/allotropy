from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import tempfile
from typing import Any
from unittest import mock
import warnings

from deepdiff import DeepDiff
from deepdiff.model import DiffLevel
from deepdiff.operator import BaseOperator
import numpy as np

from allotropy.allotrope.converter import structure
from allotropy.constants import ASM_CONVERTER_VERSION, DEFAULT_ENCODING
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file

DictType = Mapping[str, Any]


def _replace_asm_converter_version(allotrope_dict: DictType) -> DictType:
    new_dict = dict(allotrope_dict)
    for key, value in new_dict.items():
        if key == "data system document":
            value["ASM converter version"] = ASM_CONVERTER_VERSION
        if isinstance(value, dict):
            _replace_asm_converter_version(value)

    return new_dict


# List of keys in ASM with "identifier" that do not need to be unique.
# Currently, only "measurement identifier" and "calculated data document" identifier should be unique.
# However, it is better to have positive exceptions, so we don't accidentally miss a newly added unique identifier.
NON_UNIQUE_IDENTIFIERS = {
    "acquisition method identifier",
    "analytical method identifier",
    "assay bead identifier",
    "batch identifier",
    "data source identifier",
    "device identifier",
    "device method identifier",
    "experimental data identifier",
    "flow cell identifier",
    "group identifier",
    "ifc identifier",
    "ligand identifier",
    "injection identifier",
    "location identifier",
    "source location identifier",
    "destination location identifier",
    "measurement method identifier",
    "sample identifier",
    "sensor chip identifier",
    "well location identifier",
    "source well location identifier",
    "destination well location identifier",
    "well plate identifier",
    "source well plate identifier",
    "destination well plate identifier",
    "well identifier",
    "assay identifier",
    "container identifier",
    "identifier role",
    "data region identifier",
    "x coordinate dimension identifier",
    "y coordinate dimension identifier",
    "parent data region identifier",
    "parent population identifier",
    "dimension identifier",
    "method identifier",
    "experiment identifier",
    "identifier",
}

VALID_CALC_DATA_SOURCES = {
    "measurement identifier",
    "calculated data identifier",
    "report point identifier",
    "analyte identifier",
    "distribution identifier",
    "identifier",
    "data region identifier",
    "experimental data identifier",
}

PATH_KEYS = {
    "POSIX path",
    "UNC path",
}


class PathComparison(BaseOperator):  # type: ignore[misc]
    # give_up_diffing stops diffing if returning True, here we use it to do a "real" comparison on path-like
    # leaf values. Because we only return True if we deem the paths equal, it's not really "giving up".
    def give_up_diffing(
        self, level: DiffLevel, diff_instance: DeepDiff  # noqa: ARG002
    ) -> bool:
        paths = [
            PureWindowsPath(raw_path) if "\\" in raw_path else PurePosixPath(raw_path)
            for raw_path in (level.t1, level.t2)
        ]
        return set(paths[0].parts) == set(paths[1].parts)


DEEPDIFF_PATH_COMPARATOR = PathComparison([f"{path_key}']$" for path_key in PATH_KEYS])


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
        elif "identifier" in key:
            all_identifiers[key].append(value)
    return {key: list(value) for key, value in all_identifiers.items()}


def _get_all_with_key(target_key: str, item: Any) -> list[Any]:
    return _get_all_with_keys({target_key}, item)


def _get_all_with_keys(target_keys: set[str], item: Any) -> list[Any]:
    values = []
    if isinstance(item, dict):
        for key, value in item.items():
            if key in target_keys:
                values.append(value)
            else:
                values.extend(_get_all_with_keys(target_keys, value))
    elif isinstance(item, list):
        for value in item:
            values.extend(_get_all_with_keys(target_keys, value))
    return values


def _validate_identifiers(asm: DictType) -> None:
    identifiers = _get_all_identifiers(asm)

    # Validate that all identifiers are unique.
    for key, value in identifiers.items():
        if key in NON_UNIQUE_IDENTIFIERS:
            continue
        if len(value) != len(set(value)):
            non_unique = [id_ for id_ in set(value) if value.count(id_) > 1]
            msg = f"Detected non-unique identifiers for key '{key}'. If this key should allow repeat values, add to NON_UNIQUE_IDENTIFIERS. Identifiers: {non_unique}"
            raise AssertionError(msg)

    # Validate that data source identifiers have a valid reference.
    data_source_ids = set(_get_all_with_key("data source identifier", asm))
    source_ids = set(_get_all_with_keys(VALID_CALC_DATA_SOURCES, asm))
    invalid_sources = data_source_ids - source_ids
    if invalid_sources:
        msg = f"data source identifiers {invalid_sources} do not have a valid identifier reference in the document."
        raise AssertionError(msg)


def _assert_allotrope_dicts_equal(
    expected: DictType,
    actual: DictType,
) -> None:
    expected_replaced = _replace_asm_converter_version(expected)
    ddiff = DeepDiff(
        expected_replaced,
        actual,
        ignore_type_in_groups=[(float, np.float64)],
        ignore_nan_inequality=True,
        custom_operators=[DEEPDIFF_PATH_COMPARATOR],
    )
    if ddiff:
        msg = f"allotropy output != expected: \n{ddiff.pretty()}"
        raise AssertionError(msg)


def _check_allotrope_dicts_for_deletions(
    expected: DictType,
    actual: DictType,
) -> tuple[bool, list[str]]:
    """
    Check if the actual dict has any deleted fields compared to expected dict.

    Returns:
        tuple[bool, list[str]]: (has_deletions, deleted_paths)
        - has_deletions: True if any fields were deleted
        - deleted_paths: List of JSON paths for deleted fields
    """
    expected_replaced = _replace_asm_converter_version(expected)
    ddiff = DeepDiff(
        expected_replaced,
        actual,
        ignore_type_in_groups=[(float, np.float64)],
        ignore_nan_inequality=True,
        custom_operators=[DEEPDIFF_PATH_COMPARATOR],
    )

    deleted_paths = []
    if ddiff:
        # Check for dictionary item removals
        if "dictionary_item_removed" in ddiff:
            for path in ddiff["dictionary_item_removed"]:
                deleted_paths.append(str(path))

        # Check for iterable item removals (list items)
        if "iterable_item_removed" in ddiff:
            for path in ddiff["iterable_item_removed"]:
                deleted_paths.append(str(path))

    return len(deleted_paths) > 0, deleted_paths


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
def mock_uuid_generation(prefix: str | None = None) -> Iterator[None]:
    with mock.patch(
        "allotropy.parsers.utils.uuids._IdGeneratorFactory.get_id_generator",
        return_value=TestIdGenerator(prefix),
    ):
        yield


ROOT_DIR = Path(__file__).parent.parent.parent.parent


def get_testdata_dir(test_filepath: str) -> Path:
    return Path(Path(test_filepath).parent.relative_to(ROOT_DIR), "testdata")


def from_file(
    test_file: Path | str, vendor: Vendor, encoding: str | None = None
) -> DictType:
    with mock_uuid_generation(vendor.name):
        return allotrope_from_file(str(test_file), vendor, encoding=encoding)


def _oneline_number_lists(contents: str) -> str:
    contents = re.sub(r"\[\s+(\d+\.?\d*)\s+\]", r"[\1]", contents)
    contents = re.sub(r"\[\s+(\d+\.?\d*),", r"[\1,", contents)
    contents = re.sub(r"\s+(\d+\.?\d*),", r" \1,", contents)
    return re.sub(r"\s+(\d+\.?\d*)\s+\]", r" \1]", contents)


def _write_actual_to_expected(
    allotrope_dict: DictType, expected_file: Path | str
) -> None:
    with tempfile.NamedTemporaryFile(mode="w+", encoding="UTF-8", delete=False) as tmp:
        tmp.write(
            _oneline_number_lists(
                json.dumps(allotrope_dict, indent=4, ensure_ascii=False)
            )
        )
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
    force_overwrite: bool = False,  # noqa: FBT001, FBT002
) -> None:
    """Use the newly created allotrope_dict to validate the contents inside expected_file."""
    # Ensure that allotrope_dict can be written via json.dump()
    with tempfile.TemporaryFile(mode="w+", encoding=DEFAULT_ENCODING) as tmp:
        json.dump(allotrope_dict, tmp, ensure_ascii=False)

    try:
        with open(expected_file, encoding=DEFAULT_ENCODING) as f:
            expected_dict = json.load(f)

        # Check for deletions before doing the assertion if we're going to overwrite
        if write_actual_to_expected_on_fail:
            has_deletions, deleted_paths = _check_allotrope_dicts_for_deletions(
                expected_dict, allotrope_dict
            )

            if has_deletions and not force_overwrite:
                # Show a summary of deleted fields instead of the full list
                if len(deleted_paths) <= 10:
                    # Show all paths if there are few
                    deleted_paths_str = "\n".join(
                        f"  - {path}" for path in deleted_paths
                    )
                    summary_msg = f"Fields that will be deleted:\n{deleted_paths_str}"
                else:
                    # Show first few and summary for many deletions
                    first_few = "\n".join(f"  - {path}" for path in deleted_paths[:5])
                    summary_msg = (
                        f"Fields that will be deleted (showing first 5 of {len(deleted_paths)}):\n"
                        f"{first_few}\n"
                        f"  ... and {len(deleted_paths) - 5} more fields"
                    )

                error_msg = (
                    f"DELETION DETECTED: Cannot overwrite test data for '{expected_file}'\n"
                    f"Total fields to be deleted: {len(deleted_paths)}\n\n"
                    f"{summary_msg}\n\n"
                    f"To proceed anyway, use the --force-overwrite flag.\n\n"
                    f"If you use --force-overwrite, the full list will be provided for your PR description."
                )
                raise AssertionError(error_msg)
            elif has_deletions and force_overwrite:
                # Issue warning about deletions for PR description
                deleted_paths_str = "\n".join(f"  - {path}" for path in deleted_paths)
                warning_msg = (
                    f"Fields will be deleted from '{expected_file}': {deleted_paths_str}. "
                    f"Please copy the following information into your PR description:\n"
                    f"**Fields deleted in test data:**\n"
                    f"{deleted_paths_str}"
                )
                warnings.warn(warning_msg, UserWarning, stacklevel=2)

        # Only do the assertion if we're not force overwriting
        if not (write_actual_to_expected_on_fail and force_overwrite):
            _assert_allotrope_dicts_equal(expected_dict, allotrope_dict)
        elif write_actual_to_expected_on_fail and force_overwrite:
            # Force overwrite - write the file and continue
            _write_actual_to_expected(allotrope_dict, expected_file)

    except Exception as e:
        if write_actual_to_expected_on_fail:
            if isinstance(e, FileNotFoundError):
                # File doesn't exist, safe to create
                _write_actual_to_expected(allotrope_dict, expected_file)
                msg = f"Missing expected output file '{expected_file}', writing expected output because 'write_actual_to_expected_on_fail=True'"
                raise AssertionError(msg) from e
            elif isinstance(
                e, AssertionError
            ) and "allotropy output != expected:" in str(e):
                _write_actual_to_expected(allotrope_dict, expected_file)
                msg = f"Mismatch between actual and expected for '{expected_file}', writing expected output because 'write_actual_to_expected_on_fail=True'\n\n{e}"
                raise AssertionError(msg) from e
        raise

    # Ensure that allotrope_dict can be structured back into a python model.
    structure(allotrope_dict)

    # Ensure that all IDs are unique and that data source identifiers are valid references.
    _validate_identifiers(allotrope_dict)
