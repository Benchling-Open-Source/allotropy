from enum import Enum

import numpy as np
import pandas as pd
from pandas import Index

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    read_multisheet_excel,
    SeriesData,
    split_dataframe,
)
from allotropy.parsers.utils.values import assert_not_none


class SheetNames(Enum):
    PROTOCOL_INFORMATION = "protocol information"
    TABLE_END_POINT = "table end point"
    MICROPLATE_END_POINT = "microplate end point"


class BmgLabtechSmartControlReader:
    SUPPORTED_EXTENSIONS = "xlsx"
    header: SeriesData
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents):
        raw_contents = read_multisheet_excel(
            named_file_contents.contents,
            header=None,
            engine="calamine",
        )
        contents = {
            name.lower(): df.replace(np.nan, None) for name, df in raw_contents.items()
        }
        self.header = self._get_headers(contents[SheetNames.PROTOCOL_INFORMATION.value])
        self.data = self._get_data(contents[SheetNames.TABLE_END_POINT.value])

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
