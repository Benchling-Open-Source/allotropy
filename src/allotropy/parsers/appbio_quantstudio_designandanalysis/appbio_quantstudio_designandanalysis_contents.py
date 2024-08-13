from __future__ import annotations

from pathlib import PureWindowsPath

import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    assert_not_empty_df,
    read_multisheet_excel,
    SeriesData,
)
from allotropy.parsers.utils.values import (
    assert_not_none,
)


class DesignQuantstudioContents:
    @staticmethod
    def create(named_file_contents: NamedFileContents) -> DesignQuantstudioContents:
        if not named_file_contents.original_file_name.endswith("xlsx"):
            extension = PureWindowsPath(named_file_contents.original_file_name).suffix
            msg = f"Invalid file extension for AppBio QuantStudio Design & Analysis: '{extension}', must be 'xlsx'"
            raise AllotropeConversionError(msg)
        return DesignQuantstudioContents(
            read_multisheet_excel(
                named_file_contents.contents,
                header=None,
                engine="calamine",
            )
        )

    def __init__(self, raw_contents: dict[str, pd.DataFrame]) -> None:
        contents = {
            str(name): df.replace(np.nan, None) for name, df in raw_contents.items()
        }
        self.header = self._get_header(contents)
        self.data = self._get_data(
            contents,
        )

    def _get_header_size(self, sheet: pd.DataFrame) -> int:
        # Find the first blank line
        for idx, * (title, *_) in sheet.itertuples():
            if title is None:
                return int(idx)
        msg = "Invalid file format, expected a blank line indicating the end of the header section."
        raise AllotropeConversionError(msg)

    def _get_header(self, contents: dict[str, pd.DataFrame]) -> SeriesData:
        sheet = assert_not_none(
            contents.get("Results"),
            msg="Unable to find 'Results' sheet.",
        )

        header_size = self._get_header_size(sheet)

        data = {}
        for _, * (title, value, *_) in sheet.iloc[:header_size].itertuples():
            data[str(title)] = None if value is None else str(value)

        header = pd.Series(data)
        header.index = header.index.str.strip()
        return SeriesData(header)

    def _get_data(self, contents: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        data_structure = {}
        for name, sheet in contents.items():
            # header_size + 1 for empty line between header and data
            header_size = self._get_header_size(sheet) + 1
            data = sheet.iloc[header_size:].reset_index(drop=True)
            data.columns = pd.Index(data.iloc[0])
            data_structure[name] = data.drop(0)
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
