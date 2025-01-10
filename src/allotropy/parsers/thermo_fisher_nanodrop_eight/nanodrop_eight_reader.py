from io import StringIO

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.utils.pandas import read_csv, SeriesData


class NanodropEightReader:
    SUPPORTED_EXTENSIONS = "txt,tsv"
    header: SeriesData
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader(read_to_lines(named_file_contents))

        header_data = {}
        # Header lines are expected to have a single 'key: value' pair, while table will have multiple
        # tab-separated column headers. So, detect header lines as:
        #   <anything but a tab>:<any number of tabs><anything but a tab><any whitespace>
        for line in reader.pop_while(match_pat=r"^[^\t]+:[\t]*[^\t]+[\s]*$"):
            key, value = line.split(":")
            header_data[key] = value.strip()

        header = pd.Series(header_data)
        header.index = header.index.astype(str).str.strip().str.lower()
        self.header = SeriesData(header)

        lines = reader.pop_csv_block_as_lines()
        if not lines:
            msg = "Reached end of file without finding table data."
            raise AllotropeConversionError(msg)

        self.data = read_csv(
            StringIO("\n".join(lines)),
            sep="\t",
            dtype={"Sample Name": str, "Sample ID": str},
            # Prevent pandas from rounding decimal values, at the cost of some speed.
            float_precision="round_trip",
        )
        self.data.columns = self.data.columns.str.lower()
