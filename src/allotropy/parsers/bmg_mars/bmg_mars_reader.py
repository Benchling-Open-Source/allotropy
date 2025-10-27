import csv
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
        try:
            self._parse_file(named_file_contents)
        except pd.errors.ParserError:
            # Fix malformed CSV files with uneven columns and retry
            named_file_contents = self._normalize_csv_columns(named_file_contents)
            self._parse_file(named_file_contents)

    def _parse_file(self, named_file_contents: NamedFileContents) -> None:
        """Parse the BMG MARS file and populate header and data attributes."""
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

    def _normalize_csv_columns(
        self, named_file_contents: NamedFileContents
    ) -> NamedFileContents:
        """Fix malformed CSV files with uneven number of columns per row.

        BMG MARS software <= v4.0 can produce CSV files where some rows have
        more or fewer columns than others. This method normalizes all rows
        to have the same number of columns by padding with empty strings,
        allowing the csv reader to parse the file correctly.

        Args:
            named_file_contents: The named file contents to fix

        Returns:
            Fixed NamedFileContents with consistent column counts
        """
        lines = read_to_lines(named_file_contents)

        if not lines:
            return named_file_contents

        # Parse all rows and find the maximum number of columns
        csv_rows = []
        max_columns = 0

        for line in lines:
            if line.strip():
                reader = csv.reader([line])
                try:
                    row = next(reader)
                    csv_rows.append(row)
                    max_columns = max(max_columns, len(row))
                except (csv.Error, StopIteration):
                    # If parsing fails, keep the original line
                    csv_rows.append([line])
                    max_columns = max(max_columns, 1)
            else:
                pass  # skip empty lines

        # Normalize all rows to have the same number of columns
        normalized_rows = []
        for row in csv_rows:
            normalized_row = row.copy()
            if len(normalized_row) < max_columns:
                # Pad with empty strings
                normalized_row.extend([""] * (max_columns - len(normalized_row)))
            elif len(normalized_row) > max_columns:
                # Truncate if somehow longer (shouldn't happen with max calculation)
                normalized_row = normalized_row[:max_columns]
            normalized_rows.append(normalized_row)

        # Convert back to CSV string
        output = StringIO()
        writer = csv.writer(output)
        writer.writerows(normalized_rows)
        output.seek(0)

        # Create a new NamedFileContents with the fixed content
        return NamedFileContents(
            contents=output,
            original_file_path=named_file_contents.original_file_path,
            encoding="utf-8",
        )
