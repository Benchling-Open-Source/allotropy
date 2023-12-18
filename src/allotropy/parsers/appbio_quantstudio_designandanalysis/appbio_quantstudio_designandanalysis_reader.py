from __future__ import annotations

from io import IOBase

import numpy as np
import pandas as pd


class DesignAndAnalysisReader:
    def __init__(self, contents: IOBase) -> None:
        self.contents = contents
        self.data = self._read_data()
        self.metadata = self._read_metadata()

    def _read_data(self) -> dict[str, pd.DataFrame]:
        skiprows = 25
        file_data = pd.read_excel(
            self.contents,
            skiprows=skiprows,
            sheet_name=None,
        )
        for _, sheet in file_data.items():
            sheet.replace(np.nan, None)
        return file_data

    def _read_metadata(self) -> pd.Series[str]:
        raw_metadata = pd.read_excel(
            self.contents,
            nrows=24,
            usecols="A:B",
            names=["index", "values"],
        ).replace(np.nan, None)

        metadata = pd.Series(raw_metadata["values"].values, index=raw_metadata["index"])
        metadata.index = metadata.index.str.strip()
        return metadata
