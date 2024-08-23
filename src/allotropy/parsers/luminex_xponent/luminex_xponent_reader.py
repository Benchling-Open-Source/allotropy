from __future__ import annotations

from io import StringIO

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.luminex_xponent import constants
from allotropy.parsers.utils.pandas import read_csv, SeriesData
from allotropy.parsers.utils.values import assert_not_none, try_float


class LuminexXponentReader:
    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader(read_to_lines(named_file_contents))

        self.header_data = self._get_header_data(reader)
        self.calibration_lines = self._get_calibration_data(reader)
        self.minimum_assay_bead_count_setting = (
            self._get_minimum_assay_bead_count_setting(reader)
        )
        self.median_data = self._get_median_data(reader)
        self.count_data = self._get_table_as_df(reader, "Count")
        self.bead_ids_data = self._get_bead_ids_data(reader)
        self.dilution_factor_data = self._get_table_as_df(reader, "Dilution Factor")
        self.errors_data = self._get_table_as_df(reader, "Warnings/Errors")

    @classmethod
    def _get_header_data(cls, reader: CsvReader) -> pd.DataFrame:
        header_lines = list(reader.pop_until(constants.CALIBRATION_BLOCK_HEADER))

        n_columns = 0
        for line in header_lines:
            n_row_columns = len(line.split(","))
            if n_row_columns > n_columns:
                n_columns = n_row_columns

        if n_columns < constants.EXPECTED_HEADER_COLUMNS:
            msg = "Unable to parse header. Not enough data."
            raise AllotropeConversionError(msg)

        header_data = read_csv(
            StringIO("\n".join(header_lines)),
            header=None,
            index_col=0,
            names=range(n_columns),
        ).dropna(how="all")

        return header_data.T

    @classmethod
    def _get_calibration_data(cls, reader: CsvReader) -> list[str]:
        reader.drop_until_inclusive(constants.CALIBRATION_BLOCK_HEADER)
        calibration_lines = reader.pop_csv_block_as_lines(
            empty_pat=constants.LUMINEX_EMPTY_PATTERN
        )
        if not calibration_lines:
            msg = "Unable to find Calibration Block."
            raise AllotropeConversionError(msg)

        return calibration_lines

    @classmethod
    def _get_minimum_assay_bead_count_setting(cls, reader: CsvReader) -> float:
        reader.drop_until(match_pat='^"?Samples"?,')
        samples_info = assert_not_none(reader.pop(), msg="Unable to find Samples info.")
        try:
            min_bead_count_setting = samples_info.replace('"', "").split(",")[3]
        except IndexError as e:
            msg = f"Unable to find minimum bead count setting in Samples info: {samples_info}."
            raise AllotropeConversionError(msg) from e

        return try_float(min_bead_count_setting, "minimum bead count setting")

    @classmethod
    def _get_median_data(cls, reader: CsvReader) -> pd.DataFrame:
        reader.drop_until_inclusive(constants.TABLE_HEADER_PATTERN.format("Median"))
        return assert_not_none(
            reader.pop_csv_block_as_df(
                empty_pat=constants.LUMINEX_EMPTY_PATTERN, header="infer"
            ),
            msg="Unable to find Median table.",
        )

    @classmethod
    def _get_bead_ids_data(cls, reader: CsvReader) -> SeriesData:
        units_df = cls._get_table_as_df(reader, "Units")
        return SeriesData(units_df.loc["BeadID:"])

    @classmethod
    def _get_table_as_df(cls, reader: CsvReader, table_name: str) -> pd.DataFrame:
        """Returns a dataframe that has the well location as index.

        Results tables in luminex xponent output files have the location as first column.
        Having this column as the index of the dataframe allows for easier lookup when
        retrieving measurement data.
        """
        reader.drop_until_inclusive(
            match_pat=constants.TABLE_HEADER_PATTERN.format(table_name)
        )

        table_lines = reader.pop_csv_block_as_lines(
            empty_pat=constants.LUMINEX_EMPTY_PATTERN
        )

        if not table_lines:
            msg = f"Unable to find {table_name} table."
            raise AllotropeConversionError(msg)

        return read_csv(
            StringIO("\n".join(table_lines)),
            header=[0],
            index_col=[0],
        ).dropna(how="all", axis="columns")
