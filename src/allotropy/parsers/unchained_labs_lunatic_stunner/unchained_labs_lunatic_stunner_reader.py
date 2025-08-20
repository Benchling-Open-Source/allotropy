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
            data = read_csv(
                named_file_contents.contents,
                header=None,
                keep_default_na=False,
            )
        else:
            data = read_excel(
                named_file_contents.contents,
                header=None,
                engine="calamine",
                keep_default_na=False,
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

        # Clean typical NA-like strings in header only so metadata parsing behaves as before
        header_block = data[:table_header_index].copy()
        if not header_block.empty:
            # Normalize header empties/NA markers to NaN so transpose+dropna collapses to 2 rows (labels+values)
            header_block = header_block.astype(object)
            previous_downcast_setting = pd.get_option("future.no_silent_downcasting")
            try:
                new_downcast_setting: bool = True
                pd.set_option("future.no_silent_downcasting", new_downcast_setting)
                header_block = header_block.replace(
                    to_replace=[r"^\s*$", r"(?i)^\s*N/?A\s*$"],
                    value=np.nan,
                    regex=True,
                ).infer_objects()
            finally:
                pd.set_option("future.no_silent_downcasting", previous_downcast_setting)
        header_data = header_block.dropna(how="all").T.dropna(how="all")
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
                parse_header_row(header_data).dropna(axis="columns", how="all")
            )
            self.header.series.index = self.header.series.index.astype(str).str.lower()

        # Rows with no Sample name are assumed to be skipped measurements, and are dropped from the results.
        data = data.dropna(subset=["sample name"])
        self.data = data.replace(np.nan, None)
