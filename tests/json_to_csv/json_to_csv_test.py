import numpy as np
import pandas as pd
import pytest

from allotropy.json_to_csv.json_to_csv import _rename_column, json_to_csv, map_dataset
from allotropy.json_to_csv.mapper_config import (
    ColumnConfig,
    DatasetConfig,
    MapperConfig,
    PivotTransformConfig,
    TransformConfig,
)


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

    actual = map_dataset(data, MapperConfig.create().datasets["dataset"])
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
    dataset_config = DatasetConfig.create(
        config_json={
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
        },
        transforms=[],
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

    actual = map_dataset(data, MapperConfig.create().datasets["dataset"])
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

    dataset_config = DatasetConfig.create(
        config_json={
            "name": "Dataset",
            "columns": [
                {
                    "name": "MyKey",
                    "path": "list1/nested/nested_key",
                }
            ],
        },
        transforms=[],
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

    actual, new_column_names = _rename_column(
        df,
        ColumnConfig(
            name="Name $key1$ $key2$",
            path="",
            include=True,
            required=False,
        ),
    )
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
    assert new_column_names == ["Name A A", "Name A B", "Name B B"]


def test_map_dataset_list_with_inconsistent_keys() -> None:
    data = {
        "list_value": [
            {
                "key1": "v1.1",
            },
            {"key1": "v2.1", "key2": "v2.2"},
        ]
    }

    actual = map_dataset(data, MapperConfig.create().datasets["dataset"])
    expected = pd.DataFrame(
        {
            "list_value.key1": ["v1.1", "v2.1"],
            "list_value.key2": [np.nan, "v2.2"],
        }
    )
    assert expected.equals(actual)


def test_map_dataset_fails_with_missing_required_column() -> None:
    dataset_config = DatasetConfig.create(
        config_json={
            "name": "Dataset",
            "columns": [
                {"name": "Required", "path": "key1", "required": True},
                {
                    "name": "Other",
                    "path": "key2",
                },
            ],
        },
        transforms=[],
    )

    map_dataset({"key1": "value1"}, dataset_config)

    with pytest.raises(ValueError, match="required"):
        map_dataset({"key2": "value1"}, dataset_config)


def test_map_dataset_with_pivot_transform() -> None:
    data = {
        "main_key": "main_value",
        "list1": [
            {
                "label": "Label1",
                "value": "list_value1",
                "id": "id1",
                "other": 1,
            },
            {
                "label": "Label2",
                "value": "list_value2",
                "id": "id1",
                "other": 2,
            },
            {
                "label": "Label1",
                "value": "list_value3",
                "id": "id2",
                "other": 1,
            },
        ],
    }

    config_json = {
        "name": "Dataset",
        "columns": [
            {
                "name": "Main",
                "path": "main_key",
            },
            {
                "name": "$label$",
                "path": "list1/value",
            },
            {"name": "label", "path": "list1/label", "include": False},
            {
                "name": "ID",
                "path": "list1/id",
            },
        ],
    }
    transforms: list[TransformConfig] = [
        PivotTransformConfig.create(
            {
                "type": "PIVOT",
                "dataset": "Dataset",
                "path": "list1",
                "value_path": "list1/value",
                "label_path": "list1/label",
            }
        )
    ]
    dataset_config = DatasetConfig.create(config_json, transforms)

    # The first and third list entries are combined into a single row because they share the same ID column.
    actual = map_dataset(data, dataset_config)
    expected = pd.DataFrame(
        {
            "Main": ["main_value", "main_value"],
            "Label1": ["list_value1", "list_value3"],
            "Label2": ["list_value2", np.nan],
            "ID": ["id1", "id2"],
        }
    )
    assert expected.equals(actual)

    # Adding column OTHER to config changes the pivot result, because now ID/OTHER are both used to determine uniqueness.
    config_json["columns"].append({"name": "OTHER", "path": "list1/other"})  # type: ignore
    dataset_config = DatasetConfig.create(config_json, transforms)
    actual = map_dataset(data, dataset_config)
    expected = pd.DataFrame(
        {
            "Main": ["main_value", "main_value", "main_value"],
            "Label1": ["list_value1", np.nan, "list_value3"],
            "Label2": [np.nan, "list_value2", np.nan],
            "ID": ["id1", "id1", "id2"],
            "OTHER": [1, 2, 1],
        }
    )
    assert expected.equals(actual)


def test_map_dataset_with_pivot_transform_with_multiple_rows_per_pivot_column() -> None:
    # This test shows that rows other than the pivot row (data_sources in this test) can be more deeply nested
    # and the pivot rows will be correctly crossed with them.
    data = {
        "calc_data": [
            {
                "name": "Name1",
                "result": {
                    "value": 1.0,
                    "unit": "s",
                },
                "data_sources": [
                    {
                        "source_id": "source_1",
                    },
                    {
                        "source_id": "source_2",
                    },
                ],
            },
            {
                "name": "Name2",
                "result": {
                    "value": 2.0,
                    "unit": "s",
                },
                "data_sources": [
                    {
                        "source_id": "source_1",
                    },
                    {
                        "source_id": "source_3",
                    },
                ],
            },
        ]
    }

    dataset_config = DatasetConfig.create(
        config_json={
            "name": "Dataset",
            "columns": [
                {
                    "name": "$name$",
                    "path": "calc_data/result/value",
                },
                {"name": "name", "path": "calc_data/name", "include": False},
                {
                    "name": "Source",
                    "path": "calc_data/data_sources/source_id",
                },
            ],
        },
        transforms=[
            PivotTransformConfig.create(
                {
                    "type": "PIVOT",
                    "dataset": "Dataset",
                    "path": "calc_data",
                    "value_path": "calc_data/result/value",
                    "label_path": "calc_data/name",
                }
            )
        ],
    )

    actual = map_dataset(data, dataset_config)
    expected = pd.DataFrame(
        {
            "Name1": [1.0, 1.0, np.nan],
            "Name2": [2.0, np.nan, 2.0],
            "Source": ["source_1", "source_2", "source_3"],
        }
    )
    assert expected.equals(actual)


def test_map_dataset_with_multiple_pivot_transform_on_one_list() -> None:
    data = {
        "list1": [
            {
                "label_1": "Label1",
                "sub_body": {
                    "sub_label": "SubLabel_1",
                    "sub_value": 1,
                },
                "value_1": "V1",
            },
            {
                "label_1": "Label1",
                "sub_body": {
                    "sub_label": "SubLabel_2",
                    "sub_value": 2,
                },
                "value_1": "V2",
            },
            {
                "label_1": "Label2",
                "sub_body": {
                    "sub_label": "SubLabel_1",
                    "sub_value": 3,
                },
                "value_1": "V3",
            },
        ]
    }

    dataset_config = DatasetConfig.create(
        config_json={
            "name": "Dataset",
            "columns": [
                {
                    "name": "label1",
                    "path": "list1/label_1",
                    "include": False,
                },
                {
                    "name": "$label1$",
                    "path": "list1/value_1",
                },
                {
                    "name": "label2",
                    "path": "list1/sub_body/sub_label",
                    "include": False,
                },
                {
                    "name": "$label2$",
                    "path": "list1/sub_body/sub_value",
                },
            ],
        },
        transforms=[
            PivotTransformConfig.create(
                {
                    "type": "PIVOT",
                    "dataset": "Dataset",
                    "path": "list1",
                    "value_path": "list1/value_1",
                    "label_path": "list1/label_1",
                }
            ),
            PivotTransformConfig.create(
                {
                    "type": "PIVOT",
                    "dataset": "Dataset",
                    "path": "list1",
                    "value_path": "list1/sub_body/sub_value",
                    "label_path": "list1/sub_body/sub_label",
                }
            ),
        ],
    )

    actual = map_dataset(data, dataset_config)
    expected = pd.DataFrame(
        {
            "Label1": ["V1", "V2", np.nan],
            "Label2": [np.nan, np.nan, "V3"],
            "SubLabel_1": [1, np.nan, 3],
            "SubLabel_2": [np.nan, 2, np.nan],
        }
    )
    assert expected.equals(actual)


def test_map_dataset_with_pivot_transform_fails_on_non_unique_value() -> None:
    # Test that we error correctly when the pivot value has conflicting values.
    data = {
        "main_key": "main_value",
        "list1": [
            {
                "label": "Label1",
                "value": "list_value1",
                "id": "id1",
            },
            {
                "label": "Label2",
                "value": "list_value2",
                "id": "id1",
            },
            {
                "label": "Label1",
                "value": "list_value3",
                "id": "id1",
            },
        ],
    }

    dataset_config = DatasetConfig.create(
        config_json={
            "name": "Dataset",
            "columns": [
                {
                    "name": "Main",
                    "path": "main_key",
                },
                {
                    "name": "$label$",
                    "path": "list1/value",
                },
                {"name": "label", "path": "list1/label", "include": False},
                {
                    "name": "ID",
                    "path": "list1/id",
                },
            ],
        },
        transforms=[
            PivotTransformConfig.create(
                {
                    "type": "PIVOT",
                    "dataset": "Dataset",
                    "path": "list1",
                    "value_path": "list1/value",
                    "label_path": "list1/label",
                }
            )
        ],
    )

    with pytest.raises(ValueError, match="Multiple unique"):
        map_dataset(data, dataset_config)


def test_map_dataset_with_join_transform() -> None:
    data = {
        "list1": [
            {"id": 1, "value": "V1.1"},
            {"id": 2, "value": "V2.1"},
        ],
        "list2": [
            {"id": 1, "value": "V2.1"},
            {"id": 2, "value": "V2.2"},
        ],
    }

    mapper_config = MapperConfig.create(
        {
            "datasets": [
                {
                    "name": "Dataset1",
                    "columns": [
                        {
                            "name": "ID",
                            "path": "list1/id",
                        },
                        {
                            "name": "Value1",
                            "path": "list1/value",
                        },
                    ],
                },
                {
                    "name": "Dataset2",
                    "include": False,
                    "columns": [
                        {
                            "name": "id2",
                            "path": "list2/id",
                        },
                        {
                            "name": "Value2",
                            "path": "list2/value",
                        },
                    ],
                },
            ],
            "transforms": [
                {
                    "type": "JOIN",
                    "dataset_1": "Dataset1",
                    "dataset_2": "Dataset2",
                    "join_key_1": "ID",
                    "join_key_2": "id2",
                }
            ],
        }
    )

    result = json_to_csv(data, mapper_config)
    assert set(result.keys()) == {"Dataset1"}
    actual = result["Dataset1"]
    assert isinstance(actual, pd.DataFrame)
    expected = pd.DataFrame(
        {
            "ID": [1, 2],
            "Value1": ["V1.1", "V2.1"],
            "Value2": ["V2.1", "V2.2"],
        }
    )
    assert expected.equals(actual)


def test_map_dataset_metadata_to_json() -> None:
    mapper_config = MapperConfig.create(
        {
            "datasets": [
                {
                    "name": "metadata",
                    "is_metadata": True,
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
                    ],
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
    }

    result = json_to_csv(data, mapper_config)
    assert set(result.keys()) == {"metadata"}
    actual = result["metadata"]
    assert isinstance(actual, dict)
    expected = {
        "First (value2)": "value1",
        "Dict Key": "dict_value",
    }
    assert expected == actual
