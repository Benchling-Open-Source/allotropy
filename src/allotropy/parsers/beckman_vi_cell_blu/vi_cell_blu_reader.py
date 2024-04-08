import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.types import IOType


class ViCellBluReader:
    @classmethod
    def read(cls, contents: IOType) -> pd.DataFrame:
        return read_csv(contents, index_col=False)
