import re
from typing import ClassVar

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.values import assert_not_none


class BeckmanCoulterBiomekReader:
    SUPPORTED_EXTENSIONS = "csv,log"
    header: SeriesData
    data: pd.DataFrame

    # Fixed column names based on headerless files
    FIXED_COLUMN_NAMES: ClassVar[list[str]] = [
        "Time Stamp",
        "Pod",
        "Transfer Step",
        "Deck Position",
        "Labware Name",
        "Labware Barcode",
        "Well Index",
        "Sample Name",
        "Probe",
        "Amount",
        "Liquid Handling Technique",
    ]

    def _looks_like_data_line(self, line: str) -> bool:
        """
        Check if a line looks like data rather than metadata.
        Data lines should have a date/time pattern as the first field.
        """
        parts = line.split(",")
        if len(parts) < 3:
            return False

        first_part = parts[0].strip()
        # Check if first part looks like a timestamp (contains numbers and slashes or dashes)
        # Examples: "08/15/2025 10:59:55", "9/4/24 14:15"
        timestamp_pattern = r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+\d{1,2}:\d{2}"
        return bool(re.match(timestamp_pattern, first_part))

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader.create(named_file_contents)

        # Check if this file has a header line by looking for "Well Index"
        has_header_line = any("Well Index" in line for line in reader.lines)

        if has_header_line:
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
        else:
            # Handle headerless files
            header_lines = []
            data_lines = []

            for raw_line in reader.lines:
                line = raw_line.strip()
                if not line:
                    continue

                if self._looks_like_data_line(line):
                    data_lines.append(line)
                else:
                    header_lines.append(line)

            # Parse header metadata
            header_dict = {}
            for line in header_lines:
                split = line.split(",")[0].split("=", maxsplit=1)
                if len(split) != 2:
                    continue
                header_dict[split[0].strip()] = split[1].strip()

            self.header = SeriesData(pd.Series(header_dict))

            # Create a new reader with just the data lines
            data_reader = CsvReader(data_lines)
            self.data = assert_not_none(
                data_reader.pop_csv_block_as_df(
                    header=None, names=self.FIXED_COLUMN_NAMES
                ),
                "Cannot parse empty dataset",
            )
