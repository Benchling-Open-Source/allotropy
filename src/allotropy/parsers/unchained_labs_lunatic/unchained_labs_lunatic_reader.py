import numpy as np
import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    assert_not_empty_df,
    df_to_series_data,
    parse_header_row,
    read_csv,
    read_excel,
    SeriesData,
    split_header_and_data,
)


class UnchainedLabsLunaticReader:
    SUPPORTED_EXTENSIONS = "csv,xlsx"
    data: pd.DataFrame
    header: SeriesData

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        if named_file_contents.extension == "csv":
            data = read_csv(named_file_contents.contents)
        else:
            data = read_excel(named_file_contents.contents)

        assert_not_empty_df(data, "Unable to parse data from empty dataset.")

        if data.columns[0] == "Report":
            header_data, data = split_header_and_data(
                data, lambda row: row.iloc[0] == "Table"
            )
            self.header = df_to_series_data(parse_header_row(header_data.T))
            data = parse_header_row(data)
        else:
            # Use the first row in the data block for metadata, since it has all required columns.
            self.header = df_to_series_data(data, index=0)

        data.columns = data.columns.str.replace("\n", " ").str.replace("\r", "")
        self.data = data.replace(np.nan, None)
