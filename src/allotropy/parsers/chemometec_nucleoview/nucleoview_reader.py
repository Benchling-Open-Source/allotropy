import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.types import IOType


class NucleoviewReader:
    @classmethod
    def read(cls, contents: IOType) -> pd.DataFrame:
        df = read_csv(contents, sep=";", skipinitialspace=True, index_col=0,)[
            :-1
        ].dropna(axis=0, how="all")

        raw_data = df.T
        raw_data = raw_data.rename(
            {"Estimated cell diameter [um]": "Estimated cell diameter (um)"},
            axis="columns",
        )
        return raw_data
