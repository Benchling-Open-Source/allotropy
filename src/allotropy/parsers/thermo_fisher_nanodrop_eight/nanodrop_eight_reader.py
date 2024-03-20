from io import StringIO

import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers import lines_reader
from allotropy.parsers.lines_reader import CsvReader


class NanoDropEightReader:
    @classmethod
    def read(cls, named_file_contents: NamedFileContents) -> pd.DataFrame:
        all_lines = lines_reader.read_to_lines(named_file_contents)
        reader = CsvReader(all_lines)
        lines = reader.pop_csv_block_as_lines()
        raw_data = read_csv(
            StringIO("\n".join(lines)),
            sep="\t",
            dtype={"Plate ID": str, "Sample ID": str},
            # Prevent pandas from rounding decimal values, at the cost of some speed.
            float_precision="round_trip",
        )
        raw_data = raw_data.rename(columns=lambda x: x.strip().lower())

        return raw_data
