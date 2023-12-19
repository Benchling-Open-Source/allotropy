import numpy as np

from allotropy.parsers.pandas_utils import read_csv
from allotropy.types import IOType


class AbsoluteQReader:
    def __init__(self, contents: IOType):
        absolute_q_data = read_csv(
            filepath_or_buffer=contents, parse_dates=["Date"]
        ).replace(np.nan, None)
        self.wells = absolute_q_data.dropna(subset=["Name"])
        self.group_rows = absolute_q_data[absolute_q_data["Name"].isna()]
