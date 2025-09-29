import re
from typing import ClassVar

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_coulter_biomek.constants import (
    FileFormat,
    PIPETTING_COLUMNS,
    UNIFIED_PIPETTING_COLUMNS,
    UNIFIED_TRANSFER_COLUMNS,
)
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.values import assert_not_none


class BeckmanCoulterBiomekReader:
    SUPPORTED_EXTENSIONS = "csv,log"
    header: SeriesData
    data: pd.DataFrame
    file_format: FileFormat

    # Fixed column names based on headerless files - keeping for backwards compatibility
    FIXED_COLUMN_NAMES: ClassVar[list[str]] = UNIFIED_PIPETTING_COLUMNS

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

    def _detect_file_format(self, data_lines: list[str], filename: str) -> FileFormat:
        """
        Detect the file format based on column count and filename patterns.
        """
        if not data_lines:
            # Default to unified pipetting for empty files
            return FileFormat.UNIFIED_PIPETTING

        # Count columns in first data line
        column_count = len(data_lines[0].split(","))

        # Check filename patterns first
        filename_lower = filename.lower()
        if "unifiedtransfer" in filename_lower:
            return FileFormat.UNIFIED_TRANSFER
        elif "pipetting" in filename_lower and "unified" not in filename_lower:
            return FileFormat.PIPETTING

        # Fall back to column count detection
        if column_count == 13:
            return FileFormat.UNIFIED_TRANSFER
        elif column_count == 9:
            return FileFormat.PIPETTING
        else:
            # Default to unified pipetting (11 columns)
            return FileFormat.UNIFIED_PIPETTING

    def _get_column_names(self, file_format: FileFormat) -> list[str]:
        """Get the appropriate column names for the detected file format."""
        if file_format == FileFormat.UNIFIED_TRANSFER:
            return UNIFIED_TRANSFER_COLUMNS
        elif file_format == FileFormat.PIPETTING:
            return PIPETTING_COLUMNS
        else:
            return UNIFIED_PIPETTING_COLUMNS

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
            # For files with headers, detect format from data
            data_lines = [",".join(str(val) for val in row) for row in self.data.values]
            self.file_format = self._detect_file_format(
                data_lines, named_file_contents.original_file_path
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

            # Detect file format before creating DataFrame
            self.file_format = self._detect_file_format(
                data_lines, named_file_contents.original_file_path
            )
            column_names = self._get_column_names(self.file_format)

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
                data_reader.pop_csv_block_as_df(header=None, names=column_names),
                "Cannot parse empty dataset",
            )
