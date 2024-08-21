from pathlib import PureWindowsPath

import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    assert_not_empty_df,
    read_csv,
    read_excel,
    SeriesData,
)
from allotropy.types import IOType


class UnchainedLabsLunaticReader:
    data: pd.DataFrame
    header: SeriesData

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        extension = PureWindowsPath(named_file_contents.original_file_name).suffix
        if extension == ".csv":
            self._parse_csv(named_file_contents.contents)
        elif extension == ".xlsx":
            self._parse_xlsx(named_file_contents.contents)
        else:
            msg = f"Unsupported file extension: '{extension}' expected one of 'csv' or 'xlsx'."
            raise AllotropeConversionError(msg)

    def _parse_csv(self, contents: IOType) -> None:
        self.data = read_csv(contents).replace(np.nan, None)
        assert_not_empty_df(self.data, "Unable to parse data from empty dataset.")
        # Use the first row in the data block for metadata, since it has all required columns.
        self.header = SeriesData(self.data.iloc[0])

    def _parse_xlsx(self, contents: IOType) -> None:
        self.data = read_excel(contents)

        # Parse the metadata section out and turn it into a series.
        metadata = None
        for idx, row in self.data.iterrows():
            if row.iloc[0] == "Table":
                index = int(str(idx))
                metadata = self.data[:index].T
                self.data.columns = pd.Index(self.data.iloc[index + 1]).str.replace(
                    "\n", " "
                )
                self.data = self.data[index + 2 :]
                assert_not_empty_df(
                    self.data, "Unable to parse data from empty dataset."
                )
                break

        if metadata is None:
            msg = "Unable to identify the end of metadata section, expecting a row with 'Table' at start."
            raise AllotropeParsingError(msg)

        if metadata.shape[0] < 2:  # noqa: PLR2004
            msg = "Unable to parse data after metadata section, expecting at least one row in table."
            raise AllotropeConversionError(msg)

        metadata.columns = pd.Index(metadata.iloc[0])
        self.header = SeriesData(metadata.iloc[1])
