import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    assert_not_empty_df,
    df_to_series_data,
    parse_header_row,
    read_csv,
    read_excel,
    SeriesData,
)


class UnchainedLabsLunaticReader:
    SUPPORTED_EXTENSIONS = "csv,xlsx"
    data: pd.DataFrame
    header: SeriesData

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        if named_file_contents.extension == "csv":
            data = read_csv(named_file_contents.contents, header=None)
        else:
            data = read_excel(
                named_file_contents.contents, header=None, engine="calamine"
            )

        assert_not_empty_df(data, "Unable to parse data from empty dataset.")

        # Find the header row by searching for a row with "Sample name".
        table_header_index = None
        for idx, row in data.iterrows():
            if row.str.lower().str.contains("sample name").any():
                table_header_index = int(str(idx))
                break
        if table_header_index is None:
            msg = "Unable to find a table header row with 'Sample Name'."
            raise AllotropeConversionError(msg)

        header_data = data[:table_header_index].dropna(how="all").T.dropna(how="all")
        data = parse_header_row(data[table_header_index:])

        # Fix column names in excel sheets with newlines/other whitespace.
        data.columns = (
            data.columns.astype(str)
            .str.replace("\n", " ")
            .str.replace("\r", "")
            .str.strip()
            .str.lower()
        )
        # If the table header is the first row, or the non-empty data above the table header is a single title,
        # there is no metadata header, so attempt to read metadata from the first row of the table.
        # Otherwise, read in the metadata header and save it as a single series.
        if table_header_index == 0 or header_data.shape == (1, 1):
            self.header = df_to_series_data(data, index=0)
        else:
            self.header = df_to_series_data(
                parse_header_row(header_data).dropna(axis="columns")
            )
            self.header.series.index = self.header.series.index.astype(str).str.lower()

        # Rows with no Sample name are assumed to be skipped measurements, and are dropped from the results.
        data = data.dropna(subset=["sample name"])
        self.data = data.replace(np.nan, None)
