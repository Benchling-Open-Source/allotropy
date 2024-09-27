import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import determine_encoding
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    read_csv,
    read_excel,
)


class RevvityMatrixReader:
    SUPPORTED_EXTENSIONS = "csv,xlsx"
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        if named_file_contents.extension == "csv":
            contents = named_file_contents.contents.read()
            encoding = (
                determine_encoding(contents, named_file_contents.encoding)
                if isinstance(contents, bytes)
                else None
            )
            named_file_contents.contents.seek(0)
            df = read_csv(named_file_contents.contents, encoding=encoding)
        else:
            df = read_excel(named_file_contents.contents)
            # Reading a percent value (50%) in read_excel results in a decimal: 0.5
            # Detect and adjust value back to 0-100%
            first_row = df_to_series_data(df, 0)
            viability = first_row[str, "Viability"]
            if "%" not in first_row[str, "Viability"] and float(viability) < 1:
                df["Viability"] = df["Viability"] * 100
        self.data = df
