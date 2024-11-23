import warnings

import numpy as np
import pandas as pd
from pandas.errors import ParserWarning

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_absolute_q.constants import get_dye_settings
from allotropy.parsers.utils.pandas import read_csv


class AppbioAbsoluteQReader:
    SUPPORTED_EXTENSIONS = "csv"
    data: pd.DataFrame
    common_columns: list[str]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        with warnings.catch_warnings():
            # The dataset does not have row labels, and is sometimes formatted with the wrong
            # number of commas, this does not cause any problems.
            warnings.filterwarnings(
                "ignore",
                category=ParserWarning,
                message="Length of header or names does not match length of data",
            )
            df = read_csv(named_file_contents.contents, index_col=False)

        df, self.common_columns = AppbioAbsoluteQReader.transform_if_summary_file(df)

        columns_to_rename = {}
        if "Name" in df and "Sample" not in df:
            columns_to_rename["Name"] = "Sample"
        if "Well ID" in df and "Well" not in df:
            columns_to_rename["Well ID"] = "Well"
        if "Run name" in df and "Run" not in df:
            columns_to_rename["Run name"] = "Run"

        if columns_to_rename:
            df = df.rename(columns=columns_to_rename)

        required_keys = {"Sample"}
        for key in required_keys:
            if key not in df:
                possible_keys = key
                if key in columns_to_rename:
                    possible_keys += f" or {columns_to_rename[key]}"
                msg = f"Input is missing required column '{possible_keys}'"
                raise AllotropeConversionError(msg)

        self.data = df.replace(np.nan, None)

    @staticmethod
    def transform_if_summary_file(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        # If the first row is only contains dye settings indicating where each dye setting section is,
        # this is a summary file.
        columns = list(df.columns)
        dye_setting_columns = get_dye_settings(columns)
        unnamed_columns = [col for col in columns if "unnamed" in col.lower()]
        if len(dye_setting_columns) + len(unnamed_columns) != df.shape[1]:
            return df, []

        # Get the start indices of the dye setting sections.
        dye_column_indices = [
            i for i, col in enumerate(columns) if "unnamed" not in col.lower()
        ]
        dye_column_indices.append(df.shape[1])

        # Remove the first row and reset the columns
        df.columns = pd.Index(df.iloc[0].astype(str).tolist())
        df = df[1:]

        # The columns before the first dye setting section are common columns
        base_df = df.iloc[:, : dye_column_indices[0]]
        # The group column is left blank on a ffill basis.
        base_df.loc[:, "Group"] = base_df["Group"].ffill()

        # For each dye setting, pull the columns for the section out and combine with the common columns
        # to create a dataset that looks like non-summary files, with one dye setting per row.
        dye_dfs: list[pd.DataFrame] = []
        for i, dye_setting in enumerate(dye_setting_columns):
            dye_df = df.iloc[:, dye_column_indices[i] : dye_column_indices[i + 1]]
            dye_df.loc[:, ["Dye"]] = dye_setting
            dye_dfs.append(pd.concat([base_df, dye_df], axis="columns"))

        return pd.concat(dye_dfs, axis="index"), list(base_df.columns)
