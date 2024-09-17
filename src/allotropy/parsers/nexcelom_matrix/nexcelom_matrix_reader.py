from __future__ import annotations

import pandas as pd

from allotropy.allotrope.pandas_util import read_csv, read_excel
from allotropy.exceptions import AllotropeConversionError
from allotropy.types import IOType

MILLION_CONVERSION = 1000000
MILLION_SCALE_COLS = ["Total Cells/mL", "Live Cells/mL", "Dead Cells/mL"]


class NexcelomMatrixReader:
    def __init__(self, contents: IOType) -> None:
        self.contents = contents
        self.data = self._read_data()

    def _read_data(self) -> pd.DataFrame:

        try:
            file_data = read_excel(self.contents)
        except AllotropeConversionError:
            file_data = read_csv(self.contents)
        file_data[MILLION_SCALE_COLS] = file_data[MILLION_SCALE_COLS].applymap(
            lambda x: x / MILLION_CONVERSION
        )
        return file_data
