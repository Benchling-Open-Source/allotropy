import numpy as np
import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.types import IOType


class AbsoluteQReader:
    def __init__(self, contents: IOType):
        absolute_q_data = read_csv(
            filepath_or_buffer=contents, parse_dates=["Date"]
        ).replace(np.nan, None)
        self.wells: pd.DataFrame = absolute_q_data.dropna(subset=["Name"])
        self.group_rows: pd.DataFrame = absolute_q_data[absolute_q_data["Name"].isna()]
