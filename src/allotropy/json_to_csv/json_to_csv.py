from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from allotropy.json_to_csv.mapper_config import (
    DatasetConfig,
    MapperConfig,
    PivotTransformConfig,
)


def _apply_pivot(df: pd.DataFrame, transform_config: PivotTransformConfig, config: DatasetConfig):
    print("\n PIVOT \n")
    print(df)
    print("\n")
    # Get the set of non-pivoted columns
    value_column_name = config.path_to_config[transform_config.value_path].name
    label_column_name = config.path_to_config[transform_config.label_path].name
    print(value_column_name)
    print("\n")
    other_columns = set(df.columns) - {value_column_name, label_column_name}
    print(other_columns)
    print("\n")
    # Rename columns
    df, new_column_names = _rename_column(df, value_column_name)
    config.replace_column_names(value_column_name, new_column_names)
    print("RENAMED")
    print(df)
    print("\n")

    # Drop columns that should not be included
    df = df.drop(columns=label_column_name)
    print("DROPPED")
    print(df)
    print("\n")

    # Group by non-pivot columns, and try to compress each into a single row.
    rows: list[list[Any]] = []
    for group_values, sub_df in df.groupby(list(other_columns)):
        rows.append([])
        for column in sub_df:
            value = set(sub_df[column].unique()) - {np.nan}
            if len(value) > 1:
                msg = f"Multiple non-unique values for column {column} in pivot operation for group: {group_values}."
                raise ValueError(msg)
            rows[-1].append(next(iter(value)) if value else np.nan)

    return pd.DataFrame(rows, columns=sub_df.columns)


def _map_dataset(
    data: dict[str, Any], config: DatasetConfig, current_path: Path | None = None
) -> pd.DataFrame:
    current_path = current_path or Path()
    single_values = {}
    for key, value in data.items():
        path = Path(current_path, key)
        column_config = config.get_column_config(str(path))
        if not column_config:
            continue
        if not isinstance(value, dict | list):
            single_values[column_config.name] = [value]

    df = pd.DataFrame(single_values)

    print(df)

    for key, value in data.items():
        # TODO: subpath seems wrong name
        sub_path = Path(current_path, key)
        sub_df: pd.DataFrame = pd.DataFrame()

        transforms = config.path_to_transform.get(str(sub_path), [])
        for transform in transforms:
            if isinstance(transform, PivotTransformConfig):
                if not isinstance(value, list):
                    msg = f"Invalid target for pivot transform: '{sub_path}', target must be a list."
                    raise ValueError(msg)

                # TODO: Move to validation for transform config
                if transform.value_path not in config.path_to_config:
                    msg = f"Missing column config for pivot transform value_key: {transform.value_path}"
                    raise ValueError(msg)

                if transform.label_path in config.path_to_config:
                    msg = f"Missing column config for pivot transform label_key: {transform.label_path}"
                    raise ValueError(msg)

                value_config = config.path_to_config[transform.value_path]
                label_config = config.path_to_config[transform.label_path]
                if f"${label_config.name}$" not in value_config.name:
                    msg = f"Invalid value column config for pivot transform - must have label column label ('${label_config.name}$') in value column name, got '{value_config.name}'."
                    raise ValueError(msg)

                if label_config.include:
                    msg = f"Invalid label column config for pivot transform - label column ('{transform.label_path}') must not be included in final result."
                    raise ValueError(msg)

        if isinstance(value, dict):
            sub_df = _map_dataset(value, config, sub_path)
        elif isinstance(value, list):
            sub_df = pd.concat(
                [_map_dataset(item, config, sub_path) for item in value],
                ignore_index=True,
            )

        for transform in transforms:
            if isinstance(transform, PivotTransformConfig):
                print("BEFORE")
                print(sub_df)
                sub_df = _apply_pivot(sub_df, transform, config)
                print("AFTER")
                print(sub_df)

        df = (
            df
            if sub_df.empty
            else (sub_df if df.empty else df.merge(sub_df, how="cross"))
        )

    return df


def _rename_column(df: pd.DataFrame, column_name: str) -> tuple[pd.DataFrame, list[str]]:
    if column_name not in df:
        return df, []

    # Get column names to be used for rename.
    labels = re.findall(r"\$([^\$]*)\$", column_name)
    label_values = df.loc[:, labels]

    # Get unique combinations of column names.
    unique_values = [tuple(t) for _, t in label_values.drop_duplicates().iterrows()]
    new_column_values = {
        unique_value: [np.nan] * df.shape[0] for unique_value in unique_values
    }
    # Map the unique labels to the corresponding column value.
    for index, row in df.iterrows():
        label_tuple = tuple(row.loc[labels])
        new_column_values[label_tuple][int(str(index))] = row.loc[column_name]

    insert_index = df.columns.get_loc(column_name)
    df = df.drop(columns=[column_name])

    new_column_names: list[str] = []
    for unique_tuple in unique_values:
        new_column_name = column_name
        for label, value in zip(labels, unique_tuple, strict=True):
            new_column_name = new_column_name.replace(f"${label}$", value)
        new_column_names.append(new_column_name)
        df.insert(insert_index, new_column_name, new_column_values[unique_tuple])
        insert_index += 1

    return df, new_column_names


def map_dataset(data: dict[str, Any], config: DatasetConfig) -> pd.DataFrame:
    df = _map_dataset(data, config)

    # Check that required columns are populated.
    required_columns = {column.name for column in config.columns if column.required}
    if missing_columns := required_columns - set(df.columns):
        msg = f"Mapped dataset is missing required columns: {missing_columns}"
        raise ValueError(msg)

    # Put columns in the order of the config
    if config.columns:
        df = df[[column for column in config.column_names if column in df]]

    # Sub column names
    for column in config.columns:
        if column.has_labels:
            df, _ = _rename_column(df, column.name)

    # Drop columns that should not be included
    columns_to_drop = [column.name for column in config.columns if not column.include and column.name in df]
    df = df.drop(columns=columns_to_drop)

    # Turn metadata into json blob

    return df


def json_to_csv(
    data: dict[str, Any], config: MapperConfig
) -> dict[str, pd.DataFrame | dict[str, Any]]:
    return {
        name: map_dataset(data, dataset_config)
        for name, dataset_config in config.datasets.items()
    }
