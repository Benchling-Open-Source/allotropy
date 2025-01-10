from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from allotropy.json_to_csv.mapper_config import DatasetConfig, MapperConfig


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

    for key, value in data.items():
        sub_path = Path(current_path, key)
        sub_df: pd.DataFrame = pd.DataFrame()
        if isinstance(value, dict):
            sub_df = _map_dataset(value, config, sub_path)
        elif isinstance(value, list):
            sub_df = pd.concat(
                [_map_dataset(item, config, sub_path) for item in value],
                ignore_index=True,
            )

        if str(sub_path) in config.path_to_transform:
            print(sub_path)
            print(sub_df)
            for column in config.columns:
                if column.has_labels:
                    sub_df = _rename_column(sub_df, column.name)
            print(sub_df)
            assert False

        df = (
            df
            if sub_df.empty
            else (sub_df if df.empty else df.merge(sub_df, how="cross"))
        )

    return df


def _rename_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    labels = re.findall(r"\$([^\$]*)\$", column_name)
    label_values = df.loc[:, labels]
    unique_values = [tuple(t) for _, t in label_values.drop_duplicates().iterrows()]

    new_column_values = {
        unique_value: [np.nan] * df.shape[0] for unique_value in unique_values
    }
    for index, row in df.iterrows():
        label_tuple = tuple(row.loc[labels])
        new_column_values[label_tuple][int(str(index))] = row.loc[column_name]

    insert_index = df.columns.get_loc(column_name)
    df = df.drop(columns=[column_name])

    for unique_tuple in unique_values:
        new_column_name = column_name
        for label, value in zip(labels, unique_tuple, strict=True):
            new_column_name = new_column_name.replace(f"${label}$", value)
        df.insert(insert_index, new_column_name, new_column_values[unique_tuple])
        insert_index += 1

    return df


def map_dataset(data: dict[str, Any], config: DatasetConfig) -> pd.DataFrame:
    df = _map_dataset(data, config)

    # Check that required columns are populated.
    required_columns = {column.name for column in config.columns if column.required}
    if missing_columns := required_columns - set(df.columns):
        msg = f"Mapped dataset is missing required columns: {missing_columns}"
        raise ValueError(msg)

    # Put columns in the order of the config
    if config.columns:
        df = df[[column.name for column in config.columns if column.name in df.columns]]

    # Sub column names
    for column in config.columns:
        if column.has_labels:
            df = _rename_column(df, column.name)

    # Drop columns that should not be included
    columns_to_drop = [column.name for column in config.columns if not column.include]
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
