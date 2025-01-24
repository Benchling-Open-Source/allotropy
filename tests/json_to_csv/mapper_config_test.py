import pytest

from allotropy.json_to_csv.mapper_config import (
    ColumnConfig,
    DatasetConfig,
    JoinTransformConfig,
    MapperConfig,
    PivotTransformConfig,
    TransformType,
)


def test_create_column_config_with_defaults() -> None:
    config_json = {
        "path": "key/with/all/defaults",
    }
    column_config = ColumnConfig.create(config_json)
    assert column_config.name == "key.with.all.defaults"
    assert column_config.path == "key/with/all/defaults"
    assert column_config.include
    assert not column_config.required


def test_create_column_config_override_defaults() -> None:
    config_json = {
        "name": "Key with overrides",
        "path": "path/with/overrides/value",
        "include": False,
        "required": True,
    }
    column_config = ColumnConfig.create(config_json)
    assert column_config.name == "Key with overrides"
    assert column_config.path == "path/with/overrides/value"
    assert not column_config.include
    assert column_config.required


def test_has_labels() -> None:
    assert not ColumnConfig.create({"path": "key"}).has_labels
    assert ColumnConfig.create(
        {"name": "Name with $label1$ and $label2$", "path": "key"}
    ).has_labels


def test_create_dataset_config() -> None:
    config_json = {
        "name": "Dataset",
        "is_metadata": False,
        "include": True,
        "columns": [
            {
                "name": "Column1",
                "path": "path/to/column1",
            }
        ],
    }
    dataset_config = DatasetConfig.create(config_json, [])
    assert not dataset_config.is_metadata
    assert dataset_config.include
    assert len(dataset_config.columns) == 1
    column_config = dataset_config.get_column_config("path/to/column1")
    assert column_config and column_config.name == "Column1"
    assert not dataset_config.get_column_config("missing.path")


def test_create_empty_dataset_config() -> None:
    config_json = {"name": "dataset", "columns": []}
    dataset_config = DatasetConfig.create(config_json, [])
    assert dataset_config.name == "dataset"
    assert not dataset_config.is_metadata
    assert dataset_config.include
    assert not dataset_config.columns
    column_config = dataset_config.get_column_config("missing/path")
    assert column_config and column_config.name == "missing.path"


def test_create_dataset_config_use_path_name_if_unique() -> None:
    config_json = {
        "name": "Dataset",
        "is_metadata": False,
        "include": True,
        "columns": [
            {
                "path": "path/to/key1",
                "required": False,
            },
            {
                "path": "path/to/key2",
                "include": False,
                "required": True,
            },
            {
                "path": "path/to/another/key2",
                "include": False,
                "required": True,
            },
        ],
    }
    dataset_config = DatasetConfig.create(config_json, [])
    assert dataset_config.columns[0].name == "Key1"
    assert dataset_config.columns[1].name == "path.to.key2"
    assert dataset_config.columns[2].name == "path.to.another.key2"


def test_create_dataset_config_fails_for_non_unique_name() -> None:
    config_json = {
        "name": "Dataset",
        "columns": [
            {
                "name": "Column1",
                "path": "path/to/key1",
            },
            {
                "name": "Column1",
                "path": "path/to/another/key2",
            },
        ],
    }
    with pytest.raises(ValueError, match="unique names"):
        DatasetConfig.create(config_json, [])


def test_create_dataset_config_fails_for_non_unique_path() -> None:
    config_json = {
        "name": "Dataset",
        "columns": [
            {
                "name": "Column1",
                "path": "path/to/key1",
            },
            {
                "name": "Column2",
                "path": "path/to/key1",
            },
        ],
    }
    with pytest.raises(ValueError, match="unique paths"):
        DatasetConfig.create(config_json, [])


def test_create_mapper_config_with_defaults() -> None:
    config_json = {
        "datasets": [
            {
                "name": "Dataset",
                "columns": [
                    {
                        "path": "path/to/key1",
                    },
                ],
            }
        ]
    }
    mapper_config = MapperConfig.create(config_json)

    assert mapper_config.datasets.keys() == {"Dataset"}
    assert not mapper_config.datasets["Dataset"].is_metadata
    assert mapper_config.datasets["Dataset"].include
    assert len(mapper_config.datasets["Dataset"].columns) == 1


def test_create_mapper_config_with_no_config() -> None:
    mapper_config = MapperConfig.create()

    assert mapper_config.datasets.keys() == {"dataset"}
    assert not mapper_config.datasets["dataset"].is_metadata
    assert mapper_config.datasets["dataset"].include
    assert not mapper_config.datasets["dataset"].columns


def test_create_mapper_config_with_transforms() -> None:
    config_json = {
        "datasets": [
            {
                "name": "Dataset1",
                "is_metadata": False,
                "include": True,
                "columns": [
                    {
                        "name": "$Label$",
                        "path": "path/to/key1",
                        "required": False,
                    },
                    {"path": "path/to/label", "required": False, "include": False},
                ],
            },
            {
                "name": "Dataset2",
                "is_metadata": False,
                "include": True,
                "columns": [
                    {
                        "path": "path/to/key1",
                        "required": False,
                    },
                ],
            },
        ],
        "transformations": [
            {
                "type": "PIVOT",
                "dataset": "Dataset1",
                "path": "path/to",
                "value_path": "path/to/key1",
                "label_path": "path/to/label",
            },
            {
                "type": "JOIN",
                "dataset_1": "Dataset1",
                "dataset_2": "Dataset2",
                "join_key_1": "col1",
                "join_key_2": "col2",
            },
        ],
    }
    mapper_config = MapperConfig.create(config_json)
    assert mapper_config.datasets["Dataset1"].path_to_transform == {
        "path/to": [
            PivotTransformConfig(
                type_=TransformType.PIVOT,
                dataset="Dataset1",
                path="path/to",
                value_path="path/to/key1",
                label_path="path/to/label",
            )
        ]
    }
    assert mapper_config.datasets["Dataset2"].path_to_transform == {}
    assert mapper_config.transforms == [
        JoinTransformConfig(
            type_=TransformType.JOIN,
            dataset_1="Dataset1",
            dataset_2="Dataset2",
            join_key_1="col1",
            join_key_2="col2",
        )
    ]


def test_create_mapper_config_fails_with_invalid_join_transform() -> None:
    config_json = {
        "datasets": [
            {
                "name": "Dataset1",
                "is_metadata": False,
                "include": True,
                "columns": [
                    {
                        "path": "path/to/key1",
                        "required": False,
                    },
                ],
            },
        ],
        "transformations": [
            {
                "type": "JOIN",
                "dataset_1": "Dataset1",
                "dataset_2": "Dataset2",
                "join_key_1": "col1",
                "join_key_2": "col2",
            }
        ],
    }
    with pytest.raises(ValueError, match="Invalid dataset_2"):
        MapperConfig.create(config_json)


def test_create_mapper_config_fails_with_invalid_pivot_transform() -> None:
    config_json = {
        "datasets": [
            {
                "name": "Dataset1",
                "is_metadata": False,
                "include": True,
                "columns": [
                    {
                        "path": "path/to/key1",
                        "required": False,
                    },
                ],
            },
        ],
        "transformations": [
            {
                "type": "PIVOT",
                "dataset": "Dataset1",
                "path": "path/to",
                "value_path": "path/to/key1",
                "label_path": "path/to/label",
            },
        ],
    }
    with pytest.raises(
        ValueError, match="Missing column config for pivot transform label_key"
    ):
        MapperConfig.create(config_json)
