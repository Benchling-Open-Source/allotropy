from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.pandas_util import read_csv, read_excel
from allotropy.exceptions import AllotropyParserError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DATE_HEADER,
    DEFAULT_VERSION,
    HEADINGS_TO_PARSER_HEADINGS,
    MODEL_RE,
    XrVersion,
)
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.parsers.utils.pandas import df_to_series, SeriesData
from allotropy.parsers.utils.values import assert_value_from_df


@dataclass
class ViCellData:
    data: list[SeriesData]
    file_info: SeriesData


def create_reader_data(named_file_contents: NamedFileContents) -> ViCellData:
    reader: ViCellXRReader | ViCellXRTXTReader = (
        ViCellXRTXTReader(named_file_contents)
        if named_file_contents.original_file_name.endswith("txt")
        else ViCellXRReader(named_file_contents)
    )
    return ViCellData(reader.data, reader.file_info)


class ViCellXRReader:
    data: list[SeriesData]
    series: SeriesData

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        # calamine is faster for reading xlsx, but does not read xls. For xls, let pandas pick engine.
        self.engine = (
            "calamine"
            if named_file_contents.original_file_name.endswith("xlsx")
            else None
        )
        self.contents = named_file_contents.contents
        self.file_info = self._get_file_info()
        self.file_version = self._get_file_version()
        self.data = self._read_data()

    def _read_excel(self, **kwargs: Any) -> pd.DataFrame:
        return read_excel(self.contents, engine=self.engine, **kwargs)

    def _read_data(self) -> list[SeriesData]:
        header_row = 4
        if self.file_version == XrVersion._2_04:
            header_row = 3

        header = self._get_file_header(header_row)
        skiprows = header_row + 1

        file_data = self._read_excel(skiprows=skiprows, names=header)

        # rename the columns to match the existing parser that was based on xls(x) files
        file_data.columns = pd.Index(
            [HEADINGS_TO_PARSER_HEADINGS.get(name, name) for name in file_data.columns]
        )

        # Do the datetime conversion and remove all rows that fail to pass as datetime
        # This fixes an issue where some files have a hidden invalid first row
        file_data[DATE_HEADER] = pd.to_datetime(
            assert_value_from_df(file_data, DATE_HEADER),
            format="%d %b %Y  %I:%M:%S %p",
            errors="coerce",
        )
        file_data = file_data.dropna(subset=DATE_HEADER)
        return [SeriesData(x) for _, x in file_data.iterrows()]

    def _get_file_header(self, header_row: int) -> list[str]:
        """Combine the two rows that forms the header."""
        header = (
            self._read_excel(
                nrows=2,
                skiprows=header_row,
                header=None,
            )
            .fillna("")
            .astype(str)
        )

        header_list: list[str] = header.agg(
            lambda x: " ".join(x).replace(" /ml", "/ml").strip()
        ).to_list()
        return header_list

    def _get_file_info(self) -> SeriesData:
        info: pd.Series[Any] = self._read_excel(
            nrows=3, header=None, usecols=[0]
        ).squeeze()
        info.index = pd.Index(["model", "filepath", "serial"])
        return SeriesData(info)

    def _get_file_version(self) -> XrVersion:
        raw_model = self.file_info.get(str, "model")
        if not raw_model:
            msg = f"Unable to retrive model from file info: {self.file_info}"
            raise AllotropyParserError(msg)
        match = re.match(MODEL_RE, raw_model, flags=re.IGNORECASE)
        if not match:
            return DEFAULT_VERSION
        try:
            version = match.groupdict()["version"]
        except AttributeError:
            return DEFAULT_VERSION
        # TODO: raise exception for unsupported versions
        version = ".".join(version.split(".")[0:2])
        return XrVersion(version)


class ViCellXRTXTReader:
    data: list[SeriesData]
    series: SeriesData

    def __init__(self, contents: NamedFileContents) -> None:
        self.lines = read_to_lines(contents)
        self.file_info = self._get_file_info()
        self.data = self._read_data()

    def _read_data(self) -> list[SeriesData]:
        data_frame = read_csv(
            StringIO("\n".join(self.lines)), sep=" :", index_col=0, engine="python"
        )
        file_data = df_to_series(
            data_frame.astype(str).T, "Failed to parse input file."
        )
        file_data = file_data.str.strip().replace("", None)
        file_data.index = pd.Index(
            [HEADINGS_TO_PARSER_HEADINGS.get(name, name) for name in file_data.index]
        )
        # Do the datetime conversion and remove all rows that fail to pass as datetime
        # This fixes an issue where some files have a hidden invalid first row
        file_data[DATE_HEADER] = pd.to_datetime(
            file_data[DATE_HEADER],
            format="%d %b %Y  %I:%M:%S %p",
            errors="coerce",
        )

        return [SeriesData(file_data)]

    def _get_file_info(self) -> SeriesData:
        data = self.lines

        return SeriesData(
            pd.Series(
                [data[0], data[3], data[8]],
                copy=False,
                index=["model", "filepath", "serial"],
            )
        )
