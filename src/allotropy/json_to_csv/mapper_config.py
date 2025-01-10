from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Any


class TransformType(Enum):
    PIVOT = "PIVOT"
    JOIN = "JOIN"


@dataclass
class TransformConfig:
    type_: TransformType

    @staticmethod
    def create(config_json: dict[str, Any]) -> TransformConfig:
        if "type" not in config_json:
            msg = "Must specify 'type' in transform config"
            raise ValueError(msg)
        try:
            type_ = TransformType(config_json["type"])
        except ValueError as err:
            msg = f"Invalid transform type: {config_json['type']}"
            raise ValueError(msg) from err

        if type_ == TransformType.PIVOT:
            return PivotTransformConfig(config_json)
        else:
            return JoinTransformConfig(config_json)


@dataclass
class PivotTransformConfig(TransformConfig):
    type_: TransformType
    path: str

    def __init__(self, config_json: dict[str, Any]) -> None:
        self.type_ = TransformType.JOIN
        if "path" not in config_json:
            msg = "Must specify 'path' in pivot transform config"
            raise ValueError(msg)
        self.path = config_json["path"]


@dataclass
class JoinTransformConfig(TransformConfig):
    type_: TransformType
    other: str
    join_key: str
    other_join_key: str

    def __init__(self, config_json: dict[str, Any]) -> None:
        self.type = TransformType.JOIN
        for key in ("other", "join_key", "other_join_key"):
            if key not in config_json:
                msg = f"Must specify '{key}' in join transform config"
                raise ValueError(msg)
        self.other = config_json["other"]
        self.join_key = config_json["join_key"]
        self.other_join_key = config_json["other_join_key"]


@dataclass
class ColumnConfig:
    name: str
    path: str
    include: bool
    required: bool

    def __init__(self, config_json: dict[str, Any]) -> None:
        if "path" not in config_json:
            msg = "Must specify 'path' in dataset config"
            raise ValueError(msg)
        self.path = config_json["path"]
        self.name = config_json.get("name", self.path.replace("/", "."))
        self.include = config_json.get("include", True)
        self.required = config_json.get("required", False)

    @property
    def has_labels(self) -> bool:
        return bool(re.findall(r"\$([^\$]*)\$", self.name))


@dataclass
class DatasetConfig:
    name: str
    is_metadata: bool
    include: bool
    columns: list[ColumnConfig]
    path_to_config: dict[str, ColumnConfig]
    path_to_transform: dict[str, TransformConfig]

    def __init__(self, config_json: dict[str, Any], path_to_transform: dict[str, list[TransformConfig]]) -> None:
        if "name" not in config_json:
            msg = "Must specify 'name' in dataset config"
            raise ValueError(msg)
        self.name = config_json["name"]
        self.is_metadata = config_json.get("is_metadata", False)
        self.include = config_json.get("include", True)
        if "columns" not in config_json or not isinstance(config_json["columns"], list):
            msg = "Must specify list 'columns' in dataset config"
            raise ValueError(msg)
        self.columns = [ColumnConfig(cj) for cj in config_json["columns"]]
        self.path_to_transform = path_to_transform

        # For columns without name specified, use name of leaf element, if unique
        leaf_column_names = [Path(column.path).name for column in self.columns]
        for column, column_config in zip(
            self.columns, config_json["columns"], strict=True
        ):
            if "name" in column_config:
                continue
            leaf_column_name = Path(column.path).name
            if leaf_column_name != column.name:
                if leaf_column_names.count(leaf_column_name) == 1:
                    column.name = leaf_column_name.title()

        self._validate()

        self.path_to_config = {
            column_config.path: column_config for column_config in self.columns
        }

    def _validate(self) -> None:
        # Assert all column names are different
        names = [column_config.name for column_config in self.columns]
        if not len(names) == len(set(names)):
            duplicate_names = {name for name in names if names.count(name) > 1}
            msg = f"Error parsing dataset config, all columns must have unique names, duplicate names: {duplicate_names}"
            raise ValueError(msg)

        # Assert all paths are different
        paths = [column_config.path for column_config in self.columns]
        if not len(paths) == len(set(paths)):
            duplicate_paths = {path for path in paths if paths.count(path) > 1}
            msg = f"Error parsing dataset config, all columns must have unique paths, duplicate paths: {duplicate_paths}"
            raise ValueError(msg)

    def get_column_config(self, path: str) -> ColumnConfig | None:
        # If not columns are specified, include everything with default config
        if not self.path_to_config:
            return ColumnConfig({"path": path})
        return self.path_to_config.get(path, None)


@dataclass
class MapperConfig:
    datasets: dict[str, DatasetConfig]
    transforms: list[TransformConfig]

    def __init__(self, config_json: dict[str, Any] | None = None) -> None:
        # If dataset config is not provided, create a "default config" with no columns specified. This will
        # cause all values in the json to be included.
        config_json = config_json or {"datasets": [{"name": "dataset", "columns": []}]}
        if "datasets" not in config_json:
            msg = "Must specify 'datasets' in mapper config"
            raise ValueError(msg)

        self.transforms = [TransformConfig.create(transform_config_json) for transform_config_json in config_json.get("transformations", [])]
        _path_to_transform: defaultdict[str, list[TransformConfig]] = defaultdict(list)
        for transform in self.transforms:
            _path_to_transform[getattr(transform, "path", None)] = transform
        path_to_transform = dict(_path_to_transform)
        path_to_transform.pop(None, None)  # discard transforms that do not have a path

        self.datasets = {}
        for dataset_config_json in config_json["datasets"]:
            dataset_config = DatasetConfig(dataset_config_json, path_to_transform)
            self.datasets[dataset_config.name] = dataset_config
