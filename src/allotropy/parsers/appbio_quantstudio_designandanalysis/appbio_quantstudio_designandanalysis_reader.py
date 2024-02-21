from __future__ import annotations

import numpy as np
import pandas as pd

from allotropy.types import IOType


class DesignAndAnalysisReader:
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
