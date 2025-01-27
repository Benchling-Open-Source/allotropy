import json
from pathlib import Path
from typing import Any
import warnings

from deepdiff import DeepDiff
import pandas as pd
import pytest

from allotropy.json_to_csv.json_to_csv import json_to_csv
from allotropy.json_to_csv.mapper_config import MapperConfig


def _assert_dicts_equal(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    ddiff = DeepDiff(expected, actual)
    if ddiff:
        msg = f"actual != expected: \n{ddiff.pretty()}"
        raise AssertionError(msg)


@pytest.mark.parametrize(
    "input_file,config_file,expected_results",
    [
        (
            "tests/json_to_csv/testdata/plate_reader.json",
            "tests/json_to_csv/testdata/plate_reader_well_absorbance_config.json",
            {
                "dataset": "tests/json_to_csv/testdata/plate_reader_well_absorbance_config.csv"
            },
        ),
        (
            "tests/json_to_csv/testdata/plate_reader.json",
            None,
            {"dataset": "tests/json_to_csv/testdata/plate_reader_no_config.csv"},
        ),
        (
            "tests/json_to_csv/testdata/plate_reader.json",
            "tests/json_to_csv/testdata/plate_reader_extract_calculated_data_config.json",
            {
                "dataset": "tests/json_to_csv/testdata/plate_reader_extract_calculated_data.csv"
            },
        ),
        (
            "tests/json_to_csv/testdata/plate_reader.json",
            "tests/json_to_csv/testdata/plate_reader_measurement_joined_on_calc_data.json",
            {
                "measurements": "tests/json_to_csv/testdata/plate_reader_measurement_joined_on_calc_data.csv"
            },
        ),
    ],
)
def test_json_to_csv_dataset(
    input_file: str,
    config_file: str | None,
    expected_results: dict[str, str],
    *,
    overwrite: bool,
) -> None:
    with open(input_file) as infile:
        input_json = json.load(infile)

    config = MapperConfig.create()
    if config_file:
        with open(config_file) as infile:
            config = MapperConfig.create(json.load(infile))

    results = json_to_csv(input_json, config)

    assert results.keys() == expected_results.keys()

    for name, actual in results.items():
        expected_file = expected_results[name]
        if isinstance(actual, dict):
            try:
                with open(expected_file) as f:
                    expected = json.load(f)
                _assert_dicts_equal(expected, actual)
            except Exception:
                if overwrite or not Path(expected_file).exists():
                    with open(expected_file, "w") as f:
                        json.dump(actual, f, index=4)
                raise
        elif isinstance(actual, pd.DataFrame):
            try:
                with warnings.catch_warnings():
                    # We don't care if the expected data can have mixed types in this scenario.
                    warnings.filterwarnings(
                        "ignore",
                        category=pd.errors.DtypeWarning,
                        message=".*have mixed types.*",
                    )
                    expected = pd.read_csv(
                        expected_file, na_values=[""], keep_default_na=False
                    )
                pd.testing.assert_frame_equal(expected, actual)
            except Exception:
                if overwrite or not Path(expected_file).exists():
                    actual.to_csv(expected_file, index=False)
                raise
