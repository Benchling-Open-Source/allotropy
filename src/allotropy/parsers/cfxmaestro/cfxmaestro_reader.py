from __future__ import annotations

import pandas as pd  # type: ignore

# from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents

# from allotropy.parsers.roche_cedex_hires import constants
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    read_csv,
    SeriesData,
)


class CFXMaestroReader:
    SUPPORTED_EXTENSIONS = "csv"
    header: SeriesData
    data: pd.DataFrame

    @staticmethod
    def create(named_file_contents: NamedFileContents) -> CFXMaestroReader:
        raw_contents = read_csv(named_file_contents.contents)
        return CFXMaestroReader(raw_contents)

    def __init__(self, raw_contents: pd.DataFrame) -> None:
        # Example of one way to parse data. This may work if your data is a simple dataset,
        # but will probably need some modification, or a totally different approach if the input
        # file is a different format.
        self.data = raw_contents
        # When there is no actual header, use the first row as the "header" to parse metadata from.
        self.header = df_to_series_data(self.data.head(1))
