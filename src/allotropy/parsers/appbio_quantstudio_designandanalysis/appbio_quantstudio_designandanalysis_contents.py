from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from allotropy.parsers.utils.values import (
    assert_not_empty_df,
    assert_not_none,
)
from allotropy.types import IOType


class DesignQuantstudioContents:
    def __init__(self, contents: IOType) -> None:
        self.contents = contents
        self.header = self._read_header()
        self.data = self._read_data()

    def _read_header(self) -> pd.Series[str]:
        raw_header = pd.read_excel(
            self.contents,
            nrows=24,
            usecols="A:B",
            names=["index", "values"],
            header=None,
        ).replace(np.nan, None)

        header = pd.Series(raw_header["values"].values, index=raw_header["index"])
        header.index = header.index.str.strip()
        return header

    def _read_data(self) -> dict[str, pd.DataFrame]:
        file_data = pd.read_excel(
            self.contents,
            skiprows=24,
            sheet_name=None,
        )
        for sheet in file_data.values():
            sheet.replace(np.nan, None, inplace=True)
        return file_data

    def get_sheet_or_none(self, sheet_name: str) -> Optional[pd.DataFrame]:
        return self.data.get(sheet_name)

    def get_non_empty_sheet_or_none(self, sheet_name: str) -> Optional[pd.DataFrame]:
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
