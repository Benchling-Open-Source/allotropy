from __future__ import annotations

from io import StringIO
import re

import pandas as pd

from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.luminex_xponent import constants
from allotropy.parsers.utils.pandas import read_csv
from allotropy.parsers.utils.values import assert_not_none, try_float_or_none


class LuminexXponentReader:
    SUPPORTED_EXTENSIONS = "csv"

    header_data: pd.DataFrame
    calibration_data: pd.DataFrame
    minimum_assay_bead_count_setting: float | None
    results_data: dict[str, pd.DataFrame]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader(read_to_lines(named_file_contents))

        self.header_data = self._get_header_data(reader)
        self.calibration_data = self._get_calibration_data(reader)
        self.minimum_assay_bead_count_setting = (
            self._get_minimum_assay_bead_count_setting(reader)
        )
        self.results_data = LuminexXponentReader._get_results(reader)

    @classmethod
    def _get_header_data(cls, reader: CsvReader) -> pd.DataFrame:
        header_lines = list(reader.pop_until(constants.CALIBRATION_BLOCK_HEADER))
        # Header has a weird structure where there rows have varying number of columns, so we need
        # special handling before passing to read_csv.
        n_columns = max(len(line.split(",")) for line in header_lines)
        if n_columns < constants.EXPECTED_HEADER_COLUMNS:
            msg = "Unable to parse header. Not enough data."
            raise AllotropeConversionError(msg)

        return (
            read_csv(
                StringIO("\n".join(header_lines)),
                header=None,
                index_col=0,
                names=range(n_columns),
            )
            .dropna(how="all")
            .T
        )

    @classmethod
    def _get_calibration_data(cls, reader: CsvReader) -> pd.DataFrame:
        reader.drop_until_inclusive(constants.CALIBRATION_BLOCK_HEADER)
        return assert_not_none(
            reader.pop_csv_block_as_df(constants.LUMINEX_EMPTY_PATTERN)
        )

    @classmethod
    def _get_minimum_assay_bead_count_setting(cls, reader: CsvReader) -> float | None:
        reader.drop_until(match_pat='^"?Samples"?,')
        samples_info = assert_not_none(reader.pop(), msg="Unable to find Samples info.")
        try:
            fields = samples_info.replace('"', "").split(",")
            min_bead_count_setting = fields[3].strip()
            # If the min bead count is left empty, the default value is 100, according to software manual.
            if not min_bead_count_setting:
                return 100
        except IndexError as e:
            msg = f"Unable to find minimum bead count setting in Samples info: {samples_info}."
            raise AllotropeConversionError(msg) from e

        return try_float_or_none(min_bead_count_setting)

    @staticmethod
    def _get_results(reader: CsvReader) -> dict[str, pd.DataFrame]:
        reader.drop_until_inclusive("Results")
        reader.drop_empty(constants.LUMINEX_EMPTY_PATTERN)
        results: dict[str, pd.DataFrame] = {}
        while reader.current_line_exists() and "-- CRC --" not in (reader.get() or ""):
            result_title_line = assert_not_none(reader.pop())
            match: re.Match[str] | None
            if not (
                match := re.match(constants.TABLE_HEADER_PATTERN, result_title_line)
            ):
                msg = f"Invalid header block start line: {result_title_line}"
                raise AllotropeParsingError(msg)
            result_title = match.groups()[0]
            table_data = assert_not_none(
                reader.pop_csv_block_as_df(
                    empty_pat=constants.LUMINEX_EMPTY_PATTERN, header=0, index_col=0
                )
            ).dropna(how="all", axis="columns")
            results[result_title] = table_data
            reader.drop_empty(constants.LUMINEX_EMPTY_PATTERN)

        return results
