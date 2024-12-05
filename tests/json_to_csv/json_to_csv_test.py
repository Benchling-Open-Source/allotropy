import numpy as np
import pandas as pd
import pytest

from allotropy.json_to_csv.json_to_csv import _rename_column, map_dataset
from allotropy.json_to_csv.mapper_config import DatasetConfig, MapperConfig


def test_map_dataset_simple_default_config() -> None:
    data = {
        "key1": "value1",
        "key2": "value2",
        "dict_value": {
            "dict_key": "dict_value",
        },
        "list_value": [
            {
                "list_key": "list_value1",
            },
            {
                "list_key": "list_value2",
            },
        ],
    }

    actual = map_dataset(data, MapperConfig().datasets["dataset"])
    expected = pd.DataFrame(
        {
            "key1": ["value1", "value1"],
            "key2": ["value2", "value2"],
            "dict_value.dict_key": ["dict_value", "dict_value"],
            "list_value.list_key": ["list_value1", "list_value2"],
        }
    )
    assert expected.equals(actual)


def test_map_dataset_simple_with_column_configs() -> None:
    dataset_config = DatasetConfig(
        {
            "name": "Dataset",
            "columns": [
                {
                    "name": "First ($second$)",
                    "path": "key1",
                },
                {"name": "second", "path": "key2", "include": False},
                {
                    "name": "Dict Key",
                    "path": "dict_value/dict_key",
                },
                {
                    "name": "List Key",
                    "path": "list_value/list_key",
                },
            ],
        }
    )

    data = {
        "key1": "value1",
        "key2": "value2",
        "dict_value": {
            "dict_key": "dict_value",
        },
        "list_value": [
            {
                "list_key": "list_value1",
            },
            {
                "list_key": "list_value2",
            },
        ],
    }

    actual = map_dataset(data, dataset_config)
    expected = pd.DataFrame(
        {
            "First (value2)": ["value1", "value1"],
            "Dict Key": ["dict_value", "dict_value"],
            "List Key": ["list_value1", "list_value2"],
        }
    )
    assert expected.equals(actual)


def test_map_dataset_nested() -> None:
    data = {
        "list1": [
            {
                "list_key": "list_value1",
                "nested": [{"nested_key": "v1.1"}, {"nested_key": "v1.2"}],
            },
            {
                "list_key": "list_value2",
                "nested": [{"nested_key": "v2.1"}, {"nested_key": "v2.2"}],
            },
        ]
    }

    actual = map_dataset(data, MapperConfig().datasets["dataset"])
    expected = pd.DataFrame(
        {
            "list1.list_key": [
                "list_value1",
                "list_value1",
                "list_value2",
                "list_value2",
            ],
            "list1.nested.nested_key": ["v1.1", "v1.2", "v2.1", "v2.2"],
        }
    )
    assert expected.equals(actual)

    dataset_config = DatasetConfig(
        {
            "name": "Dataset",
            "columns": [
                {
                    "name": "MyKey",
                    "path": "list1/nested/nested_key",
                }
            ],
        }
    )
    actual = map_dataset(data, dataset_config)
    expected = pd.DataFrame(
        {
            "MyKey": ["v1.1", "v1.2", "v2.1", "v2.2"],
        }
    )
    assert expected.equals(actual)


def test__rename_columns_multiple_values() -> None:
    df = pd.DataFrame(
        {
            "key1": ["A", "A", "A", "B"],
            "Name $key1$ $key2$": [1, 2, 3, 4],
            "key2": ["A", "A", "B", "B"],
        }
    )

    actual = _rename_column(df, "Name $key1$ $key2$")
    expected = pd.DataFrame(
        {
            "key1": ["A", "A", "A", "B"],
            "Name A A": [1, 2, np.nan, np.nan],
            "Name A B": [np.nan, np.nan, 3, np.nan],
            "Name B B": [np.nan, np.nan, np.nan, 4],
            "key2": ["A", "A", "B", "B"],
        }
    )
    assert actual.equals(expected)


def test_map_dataset_list_with_inconsistent_keys() -> None:
    data = {
        "list_value": [
            {
                "key1": "v1.1",
            },
            {"key1": "v2.1", "key2": "v2.2"},
        ]
    }

    actual = map_dataset(data, MapperConfig().datasets["dataset"])
    expected = pd.DataFrame(
        {
            "list_value.key1": ["v1.1", "v2.1"],
            "list_value.key2": [np.nan, "v2.2"],
        }
    )
    assert expected.equals(actual)


def test_map_dataset_fails_with_missing_required_column() -> None:
    dataset_config = DatasetConfig(
        {
            "name": "Dataset",
            "columns": [
                {"name": "Required", "path": "key1", "required": True},
                {
                    "name": "Other",
                    "path": "key2",
                },
            ],
        }
    )

    map_dataset({"key1": "value1"}, dataset_config)

    with pytest.raises(ValueError, match="required"):
        map_dataset({"key2": "value1"}, dataset_config)
