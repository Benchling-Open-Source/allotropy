from __future__ import annotations

import numpy as np
import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    assert_not_empty_df,
    df_to_series_data,
    parse_header_row,
    read_multisheet_excel,
    SeriesData,
    split_header_and_data,
)
from allotropy.parsers.utils.values import (
    assert_not_none,
)


class DesignQuantstudioReader:
    SUPPORTED_EXTENSIONS = "xlsx,xls"
    header: SeriesData
    data: dict[str, pd.DataFrame]

    @staticmethod
    def create(named_file_contents: NamedFileContents) -> DesignQuantstudioReader:
        raw_contents = read_multisheet_excel(
            named_file_contents.contents,
            header=None,
            engine="calamine",
        )
        contents = {
            str(name): df.replace(np.nan, None) for name, df in raw_contents.items()
        }
        return DesignQuantstudioReader(contents)

    def __init__(self, contents: dict[str, pd.DataFrame]) -> None:
        self.contents = contents
        self.header = self._get_header(contents)
        self.data = self._get_data(contents)

    def _get_header(self, contents: dict[str, pd.DataFrame]) -> SeriesData:
        sheet = assert_not_none(
            contents.get("Results"),
            msg="Unable to find 'Results' sheet.",
        )
        df, _ = split_header_and_data(sheet, lambda row: row[0] is None)
        return df_to_series_data(parse_header_row(df.T))

    def _get_data(self, contents: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        data_structure = {}
        for name, sheet in contents.items():
            _, data = split_header_and_data(sheet, lambda row: row[0] is None)
            data_structure[name] = parse_header_row(data.replace(np.nan, None))
        return data_structure

    def has_sheet(self, sheet_name: str) -> bool:
        return sheet_name in self.data

    def get_sheet_or_none(self, sheet_name: str) -> pd.DataFrame | None:
        return self.data.get(sheet_name)

    def get_non_empty_sheet_or_none(self, sheet_name: str) -> pd.DataFrame | None:
        sheet = self.get_sheet_or_none(sheet_name)
        return None if sheet is None or sheet.empty else sheet

    def get_sheet(self, sheet_name: str) -> pd.DataFrame:
        return assert_not_none(
            self.get_sheet_or_none(sheet_name),
            msg=f"Unable to find '{sheet_name}' sheet in file.",
        )

    def get_non_empty_sheet(self, sheet_name: str) -> pd.DataFrame:
        return assert_not_empty_df(
            self.get_sheet(sheet_name),
            msg=f"sheet '{sheet_name}' is empty.",
        )
