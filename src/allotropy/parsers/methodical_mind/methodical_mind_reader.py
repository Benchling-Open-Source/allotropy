from collections.abc import Iterator

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.values import assert_not_none


class MethodicalMindReader:
    SUPPORTED_EXTENSIONS = "txt"
    plate_headers: list[SeriesData]
    plate_data: list[pd.DataFrame]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        file_lines = read_to_lines(named_file_contents)
        reader = CsvReader(file_lines)

        self.plate_headers = []
        self.plate_data = []
        while reader.current_line_exists():
            lines = list(reader.pop_until(r"Data|Spot\s+:"))
            lines = [
                line.replace("\\t", "\t")
                for line in lines
                if "Digital_Signature" not in line
            ]
            kv_pairs = [line.split(":", 1) for line in lines if ":" in line]
            key_values = {
                key.strip(): value.strip() for key, value in kv_pairs if value.strip()
            }
            self.plate_headers.append(SeriesData(pd.Series(key_values)))

            if "Data" not in reader.get():
                # TODO get visible spots and pass them to create location ids
                reader.drop_until("Data")

            # Pop data title line
            reader.pop()

            # Create dataframe of the plate, drop any columns with all Nan values
            data = assert_not_none(
                reader.lines_as_df(
                    list(reader.pop_until("===")), sep="\t", header=0, index_col=0
                ),
                "Luminescence data table",
            ).dropna(axis="columns", how="all")
            # There may be multiple rows per well row for additional measurements, and the extra rows are
            # not labelled. ffill the row label so that each row has the corresponding row label.
            data.index = pd.Index(data.index.to_series().ffill())

            data.index = data.index.astype(str).str.strip()
            data.index = pd.Index(data.index.to_series().replace("", pd.NA).ffill())
            data.columns = data.columns.astype(str).str.strip()
            self.plate_data.append(data)

            reader.drop_until("Stack ID")

    def __iter__(self) -> Iterator[tuple[SeriesData, pd.DataFrame]]:
        yield from zip(self.plate_headers, self.plate_data, strict=True)
