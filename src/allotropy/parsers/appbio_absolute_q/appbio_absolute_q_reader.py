from io import IOBase

import pandas as pd


class AbsoluteQReader:
    def __init__(self, contents: IOBase):
        absolute_q_data = pd.read_csv(contents, parse_dates=["Date"])  # type: ignore[call-overload]
        self.wells: pd.DataFrame = absolute_q_data.dropna(subset=["Name"])
        self.group_rows: pd.DataFrame = absolute_q_data[absolute_q_data["Name"].isna()]
