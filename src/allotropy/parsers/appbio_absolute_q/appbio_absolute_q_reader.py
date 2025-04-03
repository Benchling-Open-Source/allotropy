from io import BytesIO

import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_absolute_q.constants import get_dye_settings
from allotropy.parsers.lines_reader import (
    CsvReader,
    EMPTY_STR_OR_CSV_LINE,
)
from allotropy.parsers.utils.values import assert_not_none
from allotropy.parsers.utils.zip_handler import ZipHandler

# we don't do chained assignment, disable to prevent spurious warning.
pd.options.mode.chained_assignment = None


class AppbioAbsoluteQReader:
    SUPPORTED_EXTENSIONS = "csv,zip"
    data: pd.DataFrame
    common_columns: list[str]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        file_contents = (
            NamedFileContents(
                contents=self._parse_zip_contents(
                    named_file_contents.get_bytes_stream()
                ),
                original_file_path=named_file_contents.original_file_path,
                encoding=named_file_contents.encoding,
            )
            if named_file_contents.extension == "zip"
            else named_file_contents
        )

        csv_reader = CsvReader.create(file_contents)
        df, self.common_columns = self.parse_dataframe(csv_reader)

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

    def _parse_zip_contents(self, data: BytesIO) -> BytesIO:
        zip_handler = ZipHandler(data)

        summary_files = [
            name for name in zip_handler.name_list if name.endswith("_summary.csv")
        ]
        n_files = len(summary_files)

        if n_files > 1:
            msg = "Two summary files identified in zip folder -- connector currently only expects one summary file to be present."
            raise AllotropeConversionError(msg)
        elif n_files == 0:
            msg = "No summary file identified in zip folder"
            raise AllotropeConversionError(msg)

        return zip_handler.get_file(summary_files[0])

    def parse_dataframe(self, csv_reader: CsvReader) -> tuple[pd.DataFrame, list[str]]:
        first_line = csv_reader.get()
        if not first_line:
            msg = "Can not parse empty file"
            raise AllotropeConversionError(msg)
        # If the first row only contains dye settings indicating where each dye setting section is,
        # this is a summary file.
        columns = first_line.split(",")
        dye_setting_columns = get_dye_settings(columns)
        empty_columns = [col for col in columns if not col]

        # If not a summary file, parse the csv as is
        if len(dye_setting_columns) + len(empty_columns) != len(columns):
            return (
                assert_not_none(
                    csv_reader.pop_csv_block_as_df(
                        EMPTY_STR_OR_CSV_LINE, header="infer"
                    ),
                    "Failed to parser dataframe from file.",
                ),
                [],
            )

        # Get rid of the dye section setting line and then read the rest of the csv
        # Pandas tries to rename columns with the same name in the header, so read without header
        # and then set the first row to columns and drop it.
        csv_reader.pop()
        df = assert_not_none(
            csv_reader.pop_csv_block_as_df(EMPTY_STR_OR_CSV_LINE, header=None),
            "Failed to parser dataframe from file.",
        )
        df.columns = pd.Index(df.iloc[0].astype(str).tolist())
        df = df[1:]

        # Get the start indices of the dye setting sections.
        dye_column_indices = [i for i, col in enumerate(columns) if col]
        dye_section_sizes = [
            dye_column_indices[i + 1] - dye_column_indices[i]
            for i in range(len(dye_column_indices) - 1)
        ]
        if not all(size == dye_section_sizes[0] for size in dye_section_sizes):
            msg = f"Expected length of dye sections to all be the same size, got: {dye_section_sizes}"
            raise AllotropeConversionError(msg)

        # The columns before the first and after the last dye setting section are common columns
        before_df = df.iloc[:, : dye_column_indices[0]]
        after_df = df.iloc[
            :,
            (dye_column_indices[0] + dye_section_sizes[0] * len(dye_setting_columns)) :,
        ]
        base_df = pd.concat([before_df, after_df], axis="columns")
        # The group column is left blank on a ffill basis.
        base_df.loc[:, "Group"] = base_df["Group"].ffill()

        # For each dye setting, pull the columns for the section out and combine with the common columns
        # to create a dataset that looks like non-summary files, with one dye setting per row.
        dye_dfs: list[pd.DataFrame] = []
        for dye_setting, start_index in zip(
            dye_setting_columns, dye_column_indices, strict=True
        ):
            dye_df = df.iloc[:, start_index : (start_index + dye_section_sizes[0])]
            dye_df.loc[:, "Dye"] = dye_setting
            dye_dfs.append(pd.concat([base_df, dye_df], axis="columns"))

        return pd.concat(dye_dfs, axis="index"), list(base_df.columns)
