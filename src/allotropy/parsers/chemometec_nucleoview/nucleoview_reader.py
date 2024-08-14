import pandas as pd

from allotropy.parsers.utils.pandas import read_csv
from allotropy.types import IOType


class NucleoviewReader:
    @classmethod
    def read(cls, contents: IOType) -> pd.DataFrame:
        df = read_csv(contents, sep=";", skipinitialspace=True, index_col=0)
        df = df[:-1].dropna(axis=0, how="all").T
        df = df.rename(
            {"Estimated cell diameter [um]": "Estimated cell diameter (um)"},
            axis="columns",
        )
        return df
