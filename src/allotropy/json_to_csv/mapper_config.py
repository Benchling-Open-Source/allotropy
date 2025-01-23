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
            return PivotTransformConfig.create(config_json)
        else:
            return JoinTransformConfig.create(config_json)


@dataclass
class PivotTransformConfig(TransformConfig):
    type_: TransformType
    dataset: str
    path: str
    value_key: str
    label_key: str

    @staticmethod
    def create(config_json: dict[str, Any]) -> PivotTransformConfig:
        for key in ("dataset", "path", "value_key", "label_key"):
            if key not in config_json:
                msg = f"Must specify '{key}' in pivot transform config"
                raise ValueError(msg)
        return PivotTransformConfig(
            type_=TransformType.JOIN,
            dataset=config_json["dataset"],
            path=config_json["path"],
            value_key=config_json["value_key"],
            label_key=config_json["label_key"],
        )

    @property
    def value_path(self) -> str:
        return str(Path(self.path, self.value_key))

    @property
    def label_path(self) -> str:
        return str(Path(self.path, self.label_key))


@dataclass
class JoinTransformConfig(TransformConfig):
    type_: TransformType
    dataset_1: str
    dataset_2: str
    join_key_1: str
    join_key_2: str

    @staticmethod
    def create(config_json: dict[str, Any]) -> JoinTransformConfig:
        for key in ("dataset_1", "dataset_2", "join_key_1", "join_key_2"):
            if key not in config_json:
                msg = f"Must specify '{key}' in join transform config"
                raise ValueError(msg)
        return JoinTransformConfig(
            type_=TransformType.JOIN,
            dataset_1=config_json["dataset_1"],
            dataset_2=config_json["dataset_2"],
            join_key_1=config_json["join_key_1"],
            join_key_2=config_json["join_key_2"],
        )


@dataclass
class ColumnConfig:
    name: str
    path: str
    include: bool
    required: bool

    @staticmethod
    def create(config_json: dict[str, Any]) -> ColumnConfig:
        if "path" not in config_json:
            msg = "Must specify 'path' in dataset config"
            raise ValueError(msg)
        path = str(config_json["path"])
        return ColumnConfig(
            path=path,
            name=config_json.get("name", path.replace("/", ".")),
            include=config_json.get("include", True),
            required=config_json.get("required", False),
        )

    @property
    def has_labels(self) -> bool:
        return bool(re.findall(r"\$([^\$]*)\$", self.name))


@dataclass
class DatasetConfig:
    name: str
    is_metadata: bool
    include: bool
    columns: list[ColumnConfig]
    path_to_transform: dict[str, list[TransformConfig]]
    path_to_config: dict[str, ColumnConfig]
    column_names: list[str]

    def __init__(
        self,
        name: str,
        is_metadata: bool,  # noqa: FBT001
        include: bool,  # noqa: FBT001
        columns: list[ColumnConfig],
        path_to_transform: dict[str, list[TransformConfig]],
    ) -> None:
        self.name = name
        self.is_metadata = is_metadata
        self.include = include
        self.columns = columns
        self.path_to_transform = path_to_transform
        self.path_to_config = {
            column_config.path: column_config for column_config in self.columns
        }
        self.column_names = [column_config.name for column_config in self.columns]
        self._validate()

    @staticmethod
    def create(config_json: dict[str, Any], path_to_transform: dict[str | None, list[TransformConfig]]) -> DatasetConfig:
        if "name" not in config_json:
            msg = "Must specify 'name' in dataset config"
            raise ValueError(msg)
        if "columns" not in config_json or not isinstance(config_json["columns"], list):
            msg = "Must specify list 'columns' in dataset config"
            raise ValueError(msg)

        # For columns without name specified, use name of leaf element, if unique
        columns = [ColumnConfig.create(cj) for cj in config_json["columns"]]
        leaf_column_names = [Path(column.path).name for column in columns]
        for column, column_config in zip(columns, config_json["columns"], strict=True):
            if "name" in column_config:
                continue
            leaf_column_name = Path(column.path).name
            if leaf_column_name != column.name:
                if leaf_column_names.count(leaf_column_name) == 1:
                    column.name = leaf_column_name.title()

        return DatasetConfig(
            name=config_json["name"],
            is_metadata=config_json.get("is_metadata", False),
            include=config_json.get("include", True),
            columns=columns,
            path_to_transform=path_to_transform,
        )

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

        for transform_path, transforms in self.path_to_transform.items():
            for transform in transforms:
                if isinstance(transform, PivotTransformConfig):
                    found = False
                    for path in self.path_to_config:
                        if transform_path in path:
                            found = True
                            break
                    if not found:
                        msg = f"Invalid PIVOT transform path: {transform_path} for dataset {self.name}, path not found in column configs."
                        raise ValueError(msg)

    def add_column(self, column_config: ColumnConfig) -> None:
        self.columns.append(column_config)
        self.path_to_config[column_config.path] = column_config
        self.column_names.append(column_config.name)

    def replace_column_names(self, column_name: str, new_column_names: list[str]) -> None:
        replace_index = self.column_names.index(column_name)
        self.column_names = self.column_names[:replace_index] + new_column_names + self.column_names[replace_index + 1:]

    def get_column_config(self, path: str) -> ColumnConfig | None:
        # If not columns are specified, include everything with default config
        if not self.path_to_config:
            return ColumnConfig.create({"path": path})
        return self.path_to_config.get(path, None)


@dataclass
class MapperConfig:
    datasets: dict[str, DatasetConfig]
    transforms: list[TransformConfig]

    @staticmethod
    def create(config_json: dict[str, list[dict[str, Any]]] | None = None) -> MapperConfig:
        # If dataset config is not provided, create a "default config" with no columns specified. This will
        # cause all values in the json to be included.
        config_json = config_json or {"datasets": [{"name": "dataset", "columns": []}]}
        if "datasets" not in config_json:
            msg = "Must specify 'datasets' in mapper config"
            raise ValueError(msg)

        _transforms = [TransformConfig.create(transform_config_json) for transform_config_json in config_json.get("transformations", [])]
        mapper_transforms: list[TransformConfig] = []
        dataset_transforms: defaultdict[str, defaultdict[str, list[TransformConfig]]] = defaultdict(lambda: defaultdict(list))
        for transform in _transforms:
            if isinstance(transform, PivotTransformConfig):
                dataset_transforms[transform.dataset][transform.path].append(transform)
            elif isinstance(transform, JoinTransformConfig):
                mapper_transforms.append(transform)
            else:  # NOTE: should not be possible.
                msg = f"Invalid transform: {transform}"
                raise ValueError(msg)

        datasets = {}
        for dataset_config_json in config_json["datasets"]:
            dataset_config = DatasetConfig.create(dataset_config_json, dict(dataset_transforms.get(dataset_config_json.get("name", None), {})))
            datasets[dataset_config.name] = dataset_config

        for transform in mapper_transforms:
            if isinstance(transform, JoinTransformConfig):
                if transform.dataset_1 not in datasets:
                    msg = f"Invalid dataset_1 in JOIN transform: {transform.dataset_1}"
                    raise ValueError(msg)
                if transform.dataset_2 not in datasets:
                    msg = f"Invalid dataset_2 in JOIN transform: {transform.dataset_1}"
                    raise ValueError(msg)

        return MapperConfig(
            datasets=datasets,
            transforms=mapper_transforms,
        )
