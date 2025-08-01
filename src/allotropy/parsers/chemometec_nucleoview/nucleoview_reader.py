from io import StringIO

import pandas as pd

from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError
from allotropy.parsers.utils.pandas import assert_not_empty_df, read_csv
from allotropy.types import IOType


class NucleoviewReader:
    SUPPORTED_EXTENSIONS = "csv"

    @classmethod
    def read(cls, contents: IOType) -> pd.DataFrame:
        content = contents.read()
        content_str = content.decode("UTF-8") if isinstance(content, bytes) else content
        separators = [":\t", "[;,]+"]
        last_error = None

        for sep in separators:
            try:
                df = read_csv(
                    StringIO(content_str),
                    sep=sep,
                    engine="python",
                    skipinitialspace=True,
                    index_col=0,
                )
                if df.shape[1] >= 1:
                    break
            except AllotropeParsingError as e:
                last_error = e
                continue
        else:
            if last_error:
                raise last_error

        try:
            df = df[:-1].dropna(axis="index", how="all").T
        except KeyError as e:
            msg = f"Error processing CSV data structure. The file may be corrupted or have an invalid format: {e}"
            raise AllotropeParsingError(msg) from e

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
