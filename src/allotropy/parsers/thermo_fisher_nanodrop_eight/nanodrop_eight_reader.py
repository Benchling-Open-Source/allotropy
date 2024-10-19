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
        while line := reader.get():
            if not line:
                msg = "Failed to parse file, reached end of file before parsing expected data."
                raise AllotropeConversionError(msg)
            if ":" in line:
                key, value = line.split(":")
                header_data[key.strip()] = value.strip()
            else:
                break
            reader.pop()

        header = pd.Series(header_data)
        header.index = header.index.str.lower()
        self.header = SeriesData(header)

        lines = reader.pop_csv_block_as_lines()

        self.data = read_csv(
            StringIO("\n".join(lines)),
            sep="\t",
            dtype={"Sample Name": str, "Sample ID": str},
            # Prevent pandas from rounding decimal values, at the cost of some speed.
            float_precision="round_trip",
        )
        self.data.columns = self.data.columns.str.lower()
