from __future__ import annotations

import numpy as np
import pandas as pd

from allotropy.types import IOType


class DesignAndAnalysisReader:
    def __init__(self, contents: IOType) -> None:
        self.contents = contents
        self.data = self._read_data()
        self.metadata = self._read_metadata()

    def _read_data(self) -> dict[str, pd.DataFrame]:
        file_data = pd.read_excel(
            self.contents,
            skiprows=24,
            sheet_name=None,
        )
        for sheet in file_data.values():
            sheet.replace(np.nan, None, inplace=True)
        return file_data

    def _read_metadata(self) -> pd.Series[str]:
        raw_metadata = pd.read_excel(
            self.contents,
            nrows=24,
            usecols="A:B",
            names=["index", "values"],
            header=None,
        ).replace(np.nan, None)

        metadata = pd.Series(raw_metadata["values"].values, index=raw_metadata["index"])
        metadata.index = metadata.index.str.strip()
        return metadata
