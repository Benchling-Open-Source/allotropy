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
    def __init__(self, contents_io: IOType) -> None:
        raw_contents = pd.read_excel(contents_io, header=None, sheet_name=None)
        contents = {
            str(name): df.replace(np.nan, None) for name, df in raw_contents.items()
        }

        self.header = self._get_header(contents)
        self.data = self._get_data(
            self.header.size + 1,  # plus 1 for empty line between header and data
            contents,
        )

    def _get_header(self, contents: dict[str, pd.DataFrame]) -> pd.Series[str]:
        sheet = assert_not_none(
            contents.get("Results"),
            msg="Unable to find 'Results' sheet.",
        )

        data = {}
        for _, * (title, value, *_) in sheet.itertuples():
            if title is None:
                break
            data[str(title)] = None if value is None else str(value)

        header = pd.Series(data)
        header.index = header.index.str.strip()
        return header

    def _get_data(
        self, drop_n_columns: int, contents: dict[str, pd.DataFrame]
    ) -> dict[str, pd.DataFrame]:
        data_structure = {}
        for name, sheet in contents.items():
            data = sheet.iloc[drop_n_columns:].reset_index(drop=True)
            data.columns = pd.Index(data.iloc[0])
            data_structure[name] = data.drop(0)
        return data_structure

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
