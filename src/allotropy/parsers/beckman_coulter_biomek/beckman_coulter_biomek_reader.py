import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.values import assert_not_none


class BeckmanCoulterBiomekReader:
    SUPPORTED_EXTENSIONS = "csv,log"
    header: SeriesData
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader.create(named_file_contents)

        header_lines = list(reader.pop_until(".*Well Index.*"))
        header_dict = {}
        for line in header_lines:
            split = line.split(",")[0].split("=", maxsplit=1)
            if len(split) != 2:
                continue
            header_dict[split[0].strip()] = split[1].strip()

        self.header = SeriesData(pd.Series(header_dict))
        self.data = assert_not_none(
            reader.pop_csv_block_as_df(header="infer"), "Cannot parse empty dataset"
        )
