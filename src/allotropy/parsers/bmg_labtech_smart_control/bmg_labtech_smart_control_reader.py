from enum import Enum

import numpy as np
import pandas as pd
from pandas import Index

from allotropy.exceptions import AllotropeParsingError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    read_multisheet_excel,
    SeriesData,
    split_dataframe,
)
from allotropy.parsers.utils.values import assert_not_none, try_float_or_none


class SheetNames(Enum):
    PROTOCOL_INFORMATION = "protocol information"
    TABLE_END_POINT = "table end point"
    MICROPLATE_END_POINT = "microplate end point"


class BmgLabtechSmartControlReader:
    SUPPORTED_EXTENSIONS = "xlsx"
    header: SeriesData
    data: pd.DataFrame
    average_of_blank_used: float | None

    def __init__(self, named_file_contents: NamedFileContents):
        raw_contents = read_multisheet_excel(
            named_file_contents.contents,
            header=None,
            engine="calamine",
        )
        contents = {
            name.lower(): df.replace(np.nan, None) for name, df in raw_contents.items()
        }
        for sheet_name in SheetNames:
            if sheet_name.value not in contents:
                msg = f"Sheet '{sheet_name.value}' not found"
                raise AllotropeParsingError(msg)
        self.header = self._get_headers(contents[SheetNames.PROTOCOL_INFORMATION.value])
        self.data = self._get_data(contents[SheetNames.TABLE_END_POINT.value])
        self.average_of_blank_used = self._get_average_of_blank_used(
            contents[SheetNames.MICROPLATE_END_POINT.value]
        )

    def _get_headers(self, data: pd.DataFrame) -> SeriesData:
        headers_df, settings_df = split_dataframe(
            data,
            lambda row: row.astype(str).iloc[0].strip().startswith("Basic settings"),
            include_split_row=True,
        )
        headers_df = assert_not_none(headers_df, "Headers")
        settings_df = assert_not_none(settings_df, "Settings")

        headers_df = headers_df.dropna(how="all")

        split_header = headers_df.iloc[:, 0].str.split(": ", n=1, expand=True)

        headers = pd.DataFrame(
            data=split_header[1].values, index=split_header[0], columns=["Value"]
        )
        settings_df = settings_df.dropna(how="all")
        settings_df = settings_df.set_index(settings_df.columns[0])
        settings_series = settings_df.squeeze()

        # Combine headers and settings into a single Series
        combined_series = pd.concat([headers["Value"], settings_series])
        combined_series.index = combined_series.index.str.rstrip(":")
        return SeriesData(combined_series)

    def _get_data(self, data: pd.DataFrame) -> pd.DataFrame:
        _, measurement_data = split_dataframe(
            data,
            lambda row: row.astype(str).iloc[0].strip().startswith("Well"),
            include_split_row=True,
        )
        measurement_data = assert_not_none(measurement_data, "Measurement data")
        measurement_data = measurement_data.transpose()
        measurement_data.columns = Index(measurement_data.iloc[0])
        measurement_data.columns = measurement_data.columns.map(
            lambda x: x.strip() if isinstance(x, str) else x
        )
        measurement_data = measurement_data[1:]
        return measurement_data

    def _get_average_of_blank_used(self, data: pd.DataFrame) -> float | None:
        _, average_of_blank_used_df = split_dataframe(
            data,
            lambda row: row.astype(str).iloc[14].strip().startswith("Blank"),
            include_split_row=True,
        )
        if average_of_blank_used_df is not None:
            average_of_blank_used = average_of_blank_used_df.iloc[0][14]
            return try_float_or_none(average_of_blank_used.strip().split(" ")[-1])
        return None
