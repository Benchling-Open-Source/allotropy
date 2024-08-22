import pandas as pd

from allotropy.constants import DEFAULT_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.roche_cedex_hires import constants
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    read_csv,
    read_excel,
    SeriesData,
)


class RocheCedexHiResReader:
    header: SeriesData
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> pd.DataFrame:
        if named_file_contents.original_file_name.endswith(".csv"):
            df = read_csv(
                named_file_contents.contents,
                index_col=False,
                encoding=DEFAULT_ENCODING,
            )
        elif named_file_contents.original_file_name.endswith(".xlsx"):
            df = read_excel(named_file_contents.contents.name)
        else:
            message = f"{constants.UNSUPPORTED_FILE_FORMAT_ERROR} '{named_file_contents.original_file_name}'"
            raise AllotropeConversionError(message)

        # Fix typo found in some source files.
        df.columns = df.columns.str.replace("identifer", "identifier", regex=True)
        self.data = df
        self.header = df_to_series_data(
            df.head(1), "Unable to parser header from dataset."
        )
