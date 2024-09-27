import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    read_csv,
    SeriesData,
)


class ChemometecNcViewReader:
    SUPPORTED_EXTENSIONS = "csv"
    header: SeriesData
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        self.data = read_csv(named_file_contents.contents)
        self.header = df_to_series_data(self.data.head(1))
