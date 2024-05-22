from __future__ import annotations

from typing import Any

import pandas as pd

from allotropy.allotrope.pandas_util import read_excel
from allotropy.types import IOType


class NexcelomMatrixReader:
    def __init__(self, contents: IOType) -> None:
        self.contents = contents
        self.data = self._read_data()

    def _read_excel(self, **kwargs: Any) -> pd.DataFrame:
        return read_excel(self.contents, **kwargs)

    def _read_data(self) -> pd.DataFrame:

        file_data = self._read_excel()
        return file_data
