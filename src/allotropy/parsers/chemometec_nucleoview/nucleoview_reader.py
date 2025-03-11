import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.pandas import assert_not_empty_df, read_csv
from allotropy.types import IOType


class NucleoviewReader:
    SUPPORTED_EXTENSIONS = "csv"

    @classmethod
    def read(cls, contents: IOType) -> pd.DataFrame:
        df = read_csv(
            contents, sep="[;,]+", engine="python", skipinitialspace=True, index_col=0
        )
        df = df[:-1].dropna(axis="index", how="all").T
        df = df.rename(
            {"Estimated cell diameter [um]": "Estimated cell diameter (um)"},
            axis="columns",
        )
        if "Viability (%)" not in df.columns:
            msg = "Value for Cell Viability was expected, but was not found in the input file"
            raise AllotropeConversionError(msg)
        df = df.dropna(subset=["Viability (%)"])
        df = df[df.columns.dropna()]
        return assert_not_empty_df(df, "Unable to parse data from empty dataset.")
