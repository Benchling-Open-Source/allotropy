from io import StringIO

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.utils.pandas import read_csv, SeriesData
from allotropy.parsers.utils.values import assert_not_none


class BmgMarsReader:
    SUPPORTED_EXTENSIONS = "csv"
    header: SeriesData
    data: pd.DataFrame
    header_content: str

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader(read_to_lines(named_file_contents))
        lines = list(reader.pop_until_inclusive("^,?Raw Data"))
        # Store the header contents so we can parse some values that don't have key/value
        # pairs such as wavelengths and read type.
        self.header_content = "\n".join(lines)

        # Transform header data into a single series
        raw_data = read_csv(StringIO(self.header_content), header=None)
        df = pd.melt(raw_data, value_vars=raw_data.columns.to_list()).dropna(
            axis="index"
        )
        new = df["value"].str.split(": ", expand=True, n=1)

        # Handle the case where no ": " delimiter is found, resulting in a DataFrame with only one column
        if new.shape[1] < 2:
            msg = "Unable to parse header data: no key-value pairs found with expected format."
            raise AllotropeConversionError(msg)
        self.header = SeriesData(pd.Series(new[1].values, index=new[0].str.upper()))

        # Read in the rest of the file as a dataframe
        reader.drop_empty(r"^[,\"\s]*$")
        self.data = assert_not_none(
            reader.pop_csv_block_as_df(header=0, index_col=0),
            msg="Unable to parse dataset from file.",
        )
