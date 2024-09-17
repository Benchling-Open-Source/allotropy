import pandas as pd

from allotropy.constants import DEFAULT_ENCODING
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    read_csv,
    read_excel,
    SeriesData,
)


class RocheCedexHiResReader:
    SUPPORTED_EXTENSIONS = "csv,xlsx"
    header: SeriesData
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        if named_file_contents.extension == "csv":
            df = read_csv(
                named_file_contents.contents,
                index_col=False,
                encoding=DEFAULT_ENCODING,
            )
        else:
            df = read_excel(named_file_contents.contents)

        # Fix typo found in some source files.
        df.columns = df.columns.str.replace("identifer", "identifier", regex=True)
        self.data = df
        self.header = df_to_series_data(df.head(1))
