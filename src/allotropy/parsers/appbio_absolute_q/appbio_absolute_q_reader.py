from io import IOBase

import numpy as np
import pandas as pd


class AbsoluteQReader:
    def __init__(self, contents: IOBase):
        absolute_q_data = pd.read_csv(  # type: ignore[call-overload]
            filepath_or_buffer=contents, parse_dates=["Date"]
        ).replace(np.nan, None)
        self.wells: pd.DataFrame = absolute_q_data.dropna(subset=["Name"])
        self.group_rows: pd.DataFrame = absolute_q_data[absolute_q_data["Name"].isna()]
