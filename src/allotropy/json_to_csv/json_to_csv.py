import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from allotropy.json_to_csv.mapper_config import (
    ColumnConfig,
    DatasetConfig,
    JoinTransformConfig,
    MapperConfig,
    PivotTransformConfig,
)


def _apply_join(
    datasets: dict[str, pd.DataFrame], transform_config: JoinTransformConfig
) -> dict[str, pd.DataFrame]:
    if transform_config.dataset_1 not in datasets:
        msg = (
            f"Invalid join transform, missing dataset_1: {transform_config.dataset_1}."
        )
        raise ValueError(msg)
    if transform_config.join_key_1 not in datasets[transform_config.dataset_1]:
        msg = f"Invalid join transform, dataset_1 ({transform_config.dataset_1}) is missing column for join_key_1: {transform_config.join_key_1}."
        raise ValueError(msg)
    if transform_config.dataset_2 not in datasets:
        msg = (
            f"Invalid join transform, missing dataset_2: {transform_config.dataset_2}."
        )
        raise ValueError(msg)
    if transform_config.join_key_2 not in datasets[transform_config.dataset_2]:
        msg = f"Invalid join transform, dataset_2 ({transform_config.dataset_2}) is missing column for join_key_2: {transform_config.join_key_2}."
        raise ValueError(msg)

    # Copy the dataframe to join, and rename the join key column so that it matches the first dataset.
    to_join = (
        datasets[transform_config.dataset_2]
        .copy(deep=True)
        .rename(columns={transform_config.join_key_2: transform_config.join_key_1})
    )

    # Join with left outer join
    join = datasets[transform_config.dataset_1].merge(
        to_join, on=transform_config.join_key_1, how="left", indicator=True
    )
    join = join[join["_merge"] != "right_only"].drop(columns=["_merge"])

    # Replace the original dataset.
    datasets[transform_config.dataset_1] = join
    return datasets


def _apply_pivot(
    df: pd.DataFrame, transform_config: PivotTransformConfig, config: DatasetConfig
) -> pd.DataFrame:
    # Get the set of non-pivoted columns
    value_column_config = config.path_to_config[transform_config.value_path]
    label_column_config = config.path_to_config[transform_config.label_path]
    other_columns = [
        column
        for column in df.columns
        if column not in {value_column_config.name, label_column_config.name}
    ]

    # Rename pivot value column and drop the label column
    df, new_column_names = _rename_column(df, value_column_config)
    config.replace_column_names(value_column_config.name, new_column_names)
    df = df.drop(columns=label_column_config.name)

    # Group by non-pivot columns, and compress each into a single row.
    rows: list[list[Any]] = []
    for group_values, sub_df in df.groupby(list(other_columns), dropna=False):
        rows.append([])
        for column in sub_df:
            value = {value for value in sub_df[column].unique() if not pd.isna(value)}
            if len(value) > 1:
                msg = f"Multiple unique values for column '{column}' in pivot operation for group: {group_values}: {value}."
                raise ValueError(msg)
            rows[-1].append(next(iter(value)) if value else np.nan)

    return pd.DataFrame(rows, columns=df.columns)


def _map_dataset(
    data: dict[str, Any], config: DatasetConfig, current_path: Path
) -> pd.DataFrame:
    # Map simple values from the current level
    single_values = {}
    for key, value in data.items():
        path = Path(current_path, key)
        column_config = config.get_column_config(str(path))
        if not column_config:
            continue
        if not isinstance(value, dict | list):
            single_values[column_config.name] = [value]
    df = pd.DataFrame(single_values)

    # Map nested dictionaries and lists, combining them with the base dataset.
    for key, value in data.items():
        path = Path(current_path, key)
        path_df: pd.DataFrame = pd.DataFrame()

        if isinstance(value, dict):
            path_df = _map_dataset(value, config, path)
        elif isinstance(value, list) and value:
            # NOTE: this assumes all values are consistent type (e.g. all dicts, all lists, all single values)
            if isinstance(value[0], dict):
                path_df = pd.concat(
                    [_map_dataset(item, config, path) for item in value],
                    ignore_index=True,
                )
            elif isinstance(value[0], list):
                column_config = config.get_column_config(str(path))
                df_data = {}
                if column_config:
                    for idx, list_value in enumerate(value):
                        df_data[f"{column_config.name}.{idx}"] = list_value
                else:
                    for idx, list_value in enumerate(value):
                        sub_path = Path(path, f"[{idx}]")
                        column_config = config.get_column_config(str(sub_path))
                        if not column_config:
                            continue
                        df_data[column_config.name] = list_value
                path_df = pd.DataFrame(df_data)
            else:
                column_config = config.get_column_config(str(path))
                if not column_config:
                    continue
                path_df = pd.DataFrame({column_config.name: value})

        for transform in config.path_to_transform.get(str(path), []):
            if isinstance(transform, PivotTransformConfig):
                if not isinstance(value, list):
                    msg = f"Invalid target for pivot transform: '{path}', target must be a list."
                    raise ValueError(msg)
                path_df = _apply_pivot(path_df, transform, config)
            else:  # should not be possible
                msg = f"Invalid transform type in dataset config: {transform.type_}"
                raise ValueError(msg)

        df = (
            df
            if path_df.empty
            else (path_df if df.empty else df.merge(path_df, how="cross"))
        )

    return df


def _rename_column(
    df: pd.DataFrame, column_config: ColumnConfig
) -> tuple[pd.DataFrame, list[str]]:
    if column_config.name not in df and f"{column_config.name}.0" not in df:
        return df, []

    all_column_names = [column_config.name]
    if f"{column_config.name}.0" in df:
        max_value = 0
        while f"{column_config.name}.{max_value + 1}" in df:
            max_value += 1
        all_column_names = [
            f"{column_config.name}.{idx}" for idx in range(max_value + 1)
        ]

    # Get columns to be used for labels.
    label_values = df.loc[:, column_config.labels]

    # Get unique combinations of column names.
    unique_values = [tuple(t) for _, t in label_values.drop_duplicates().iterrows()]
    new_column_values = {
        unique_value: [np.nan] * df.shape[0] for unique_value in unique_values
    }

    for column_name in all_column_names:
        # Map the unique labels to the corresponding column value.
        for index, row in df.iterrows():
            label_tuple = tuple(row.loc[column_config.labels])
            new_column_values[label_tuple][int(str(index))] = row.loc[column_name]

        # Drop the old column
        insert_index = df.columns.get_loc(column_name)
        df = df.drop(columns=[column_name])

        # Inject the new columns
        new_column_names: list[str] = []
        for unique_tuple in unique_values:
            new_column_name = column_name
            for label, value in zip(column_config.labels, unique_tuple, strict=True):
                new_column_name = new_column_name.replace(f"${label}$", str(value))
            new_column_names.append(new_column_name)
            df.insert(insert_index, new_column_name, new_column_values[unique_tuple])
            insert_index += 1

    return df, new_column_names


def map_dataset(data: dict[str, Any], config: DatasetConfig) -> pd.DataFrame:
    # NOTE: empty Path is passed as start case to private recursive function.
    df = _map_dataset(data, config, current_path=Path())

    # Check that required columns are populated.
    required_columns = {column.name for column in config.columns if column.required}
    if missing_columns := required_columns - set(df.columns):
        for missing in list(missing_columns):
            # Handle potential list expansion.
            if f"{missing}.0" in df:
                missing_columns.remove(missing)
        if missing_columns:
            msg = f"Mapped dataset is missing required columns: {missing_columns}"
            raise ValueError(msg)

    # Put columns in the order of the config
    if config.columns:
        # Handle potential list expansion.
        for column in config.columns:
            if column.name not in df and f"{column.name}.0" in df:
                max_value = 0
                while f"{column.name}.{max_value + 1}" in df:
                    max_value += 1
                config.replace_column_names(
                    column.name,
                    [f"{column.name}.{idx}" for idx in range(max_value + 1)],
                )
        df = df[[column for column in config.column_names if column in df]]

    # Rename columns with substitution labels
    for column_config in config.columns:
        if column_config.labels:
            df, _ = _rename_column(df, column_config)

    # Drop columns that should not be included
    columns_to_drop = [
        column.name
        for column in config.columns
        if not column.include and column.name in df
    ]
    df = df.drop(columns=columns_to_drop)

    return df


def _convert_to_json_blob(df: pd.DataFrame, config: DatasetConfig) -> dict[str, Any]:
    try:
        blob = json.loads(df.to_json())
    except ValueError as e:
        msg = f"Unable to convert dataset {config.name} to json blob with error: {e}"
        raise ValueError(msg) from e

    if not isinstance(blob, dict):
        msg = f"Invalid candidate for dataset to metadata json conversion for dataset {config.name} result is not a dictionary: {blob}"
        raise ValueError(msg)

    cleaned: dict[str, Any] = {}
    for key, value in blob.items():
        if not isinstance(value, dict):
            msg = f"Invalid object: {value} at key {key} when converting dataframe to json."
            raise ValueError(msg)
        if len(value) != 1:
            msg = f"Invalid candidate for dataset to metadata json conversion for key {key}: {value}. Must have a single value per key."
            raise ValueError(msg)
        cleaned[key] = value[next(iter(value))]
    return cleaned


def json_to_csv(
    data: dict[str, Any], config: MapperConfig
) -> dict[str, pd.DataFrame | dict[str, Any]]:
    datasets = {
        name: map_dataset(data, dataset_config)
        for name, dataset_config in config.datasets.items()
    }

    # Apply transforms across multiple datasets (e.g. joins)
    for transform in config.transforms:
        if isinstance(transform, JoinTransformConfig):
            _apply_join(datasets, transform)

    # Remove datasets that should not be included.
    datasets = {
        name: dataset
        for name, dataset in datasets.items()
        if config.datasets[name].include
    }

    # Convert metadata datasets to json
    result: dict[str, pd.DataFrame | dict[str, Any]] = {
        name: _convert_to_json_blob(dataset, config.datasets[name])
        if config.datasets[name].is_metadata
        else dataset
        for name, dataset in datasets.items()
    }
    return result
