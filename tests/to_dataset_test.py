import json
import warnings

import pandas as pd

from allotropy.to_dataset import map_json


def test_json_to_csv_dataset() -> None:
    input_file = "tests/json_to_csv/testdata/plate_reader.json"
    config_file = "tests/json_to_csv/testdata/plate_reader_well_absorbance_config.json"
    expected_file = "tests/json_to_csv/testdata/plate_reader_well_absorbance_config.csv"

    with open(input_file) as infile, open(config_file) as confile:
        data = json.load(infile)
        config = json.load(confile)
        results = map_json(data, config)

    assert results.keys() == {"dataset"}
    with warnings.catch_warnings():
        # We don't care if the expected data can have mixed types in this scenario.
        warnings.filterwarnings(
            "ignore",
            category=pd.errors.DtypeWarning,
            message=".*have mixed types.*",
        )
        expected = pd.read_csv(expected_file, na_values=[""], keep_default_na=False)
        actual = results["dataset"]
        assert isinstance(actual, pd.DataFrame)
        pd.testing.assert_frame_equal(expected, actual)
