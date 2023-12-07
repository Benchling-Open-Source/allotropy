from io import IOBase

import numpy as np
import pandas as pd

from allotropy.parsers.pandas_utils import read_csv


class AbsoluteQReader:
    def __init__(self, contents: IOBase):
        absolute_q_data = read_csv(
            filepath_or_buffer=contents, parse_dates=["Date"]  # type: ignore[arg-type]
        ).replace(np.nan, None)
        self.wells: pd.DataFrame = absolute_q_data.dropna(subset=["Name"])
        self.group_rows: pd.DataFrame = absolute_q_data[absolute_q_data["Name"].isna()]
