import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import (
    CsvReader,
    EMPTY_STR_OR_CSV_LINE,
)
from allotropy.parsers.utils.values import assert_not_none

# we don't do chained assignment, disable to prevent spurious warning.
pd.options.mode.chained_assignment = None


def get_first_non_empty(data: list[str]) -> int | None:
    for idx, col in enumerate(data):
        if col:
            return idx
    return None


def first_row_as_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = pd.Index(df.iloc[0].astype(str).tolist())
    return df[1:]


class AppbioAbsoluteQReader:
    SUPPORTED_EXTENSIONS = "csv"
    data: pd.DataFrame
    common_columns: list[str]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        csv_reader = CsvReader.create(named_file_contents)
        df, self.common_columns = AppbioAbsoluteQReader.parse_dataframe(csv_reader)

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
    def parse_dataframe(csv_reader: CsvReader) -> tuple[pd.DataFrame, list[str]]:
        titles = assert_not_none(
            csv_reader.pop(),
            msg="Can not parse empty file",
        ).split(",")

        info = assert_not_none(
            csv_reader.get(),
            msg="Can not parse empty file",
        ).split(",")

        first_non_empty = assert_not_none(
            get_first_non_empty(titles),
            msg="Can not parse empty file",
        )

        # A summary file only contains dye settings in the first row
        # The second row contains columns with dye settings info starting from Target until Threshold
        # If not a summary file, parse the csv as is
        if info[first_non_empty] != "Target":
            return (
                assert_not_none(
                    csv_reader.pop_csv_block_as_df(EMPTY_STR_OR_CSV_LINE, names=titles),
                    "Failed to parser dataframe from file.",
                ),
                [],
            )

        df = assert_not_none(
            csv_reader.pop_csv_block_as_df(EMPTY_STR_OR_CSV_LINE, header=None),
            "Failed to parser dataframe from file.",
        )

        dye_names = [column for column in titles if column]

        # Get the start and end indices of the dye setting sections.
        dye_start = []
        dye_end = []
        for idx, col in enumerate(info):
            if col == "Target":
                dye_start.append(idx)
            elif col == "Threshold":
                dye_end.append(idx)

        if len(dye_start) != len(dye_end) != len(dye_names):
            msg = "Unable to infer dye columns"
            raise AllotropeConversionError(msg)

        # expected size of dye settings
        dye_size = dye_end[0] - dye_start[0] + 1

        # Construct common columns
        start, end = dye_start[0], dye_end[-1]
        base_df = first_row_as_columns(
            pd.concat([df.iloc[:, :start], df.iloc[:, end + 1 :]], axis=1)
        )

        # The group column is left blank on a ffill basis.
        base_df.loc[:, "Group"] = base_df["Group"].ffill()

        # Extract each dye setting columns and combine with the common columns
        # to create a dataset that looks like non-summary files, with one dye setting per row.
        dye_dfs: list[pd.DataFrame] = []
        for start, end, name in zip(dye_start, dye_end, dye_names, strict=True):
            dye_df = first_row_as_columns(df.iloc[:, start : end + 1])

            if dye_df.shape[1] != dye_size:
                msg = f"Expected all length of dye sections to be {dye_size}, dye {name} got: {dye_df.shape[1]}"
                raise AllotropeConversionError(msg)

            dye_df.loc[:, "Dye"] = name
            dye_dfs.append(pd.concat([base_df, dye_df], axis="columns"))

        return pd.concat(dye_dfs, axis="index"), list(base_df.columns)
