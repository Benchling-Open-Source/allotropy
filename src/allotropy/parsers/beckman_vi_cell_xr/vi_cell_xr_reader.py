from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.pandas_util import read_excel
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DATE_HEADER,
    DEFAULT_VERSION,
    HEADINGS_TO_PARSER_HEADINGS,
    MODEL_RE,
    XrVersion,
)
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.values import assert_value_from_df


@dataclass
class ViCellData:
    data: pd.DataFrame
    file_info: SeriesData


def create_reader_data(named_file_contents: NamedFileContents) -> ViCellData:
    reader: ViCellXRReader | ViCellXRTXTReader = (
        ViCellXRTXTReader(named_file_contents)
        if named_file_contents.original_file_name.endswith("txt")
        else ViCellXRReader(named_file_contents)
    )
    return ViCellData(reader.data, reader.file_info)


class ViCellXRReader:
    data: pd.DataFrame
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

    def _read_data(self) -> pd.DataFrame:
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

        return file_data

    def _get_file_header(self, header_row: int) -> list[str]:
        """Combine the two rows that forms the header."""
        header = self._read_excel(
            nrows=2,
            skiprows=header_row,
            header=None,
        ).fillna("")

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
        match = re.match(MODEL_RE, self.file_info[str, "model"], flags=re.IGNORECASE)
        try:
            version = match.groupdict()["version"]  # type: ignore[union-attr]
        except AttributeError:
            return DEFAULT_VERSION
        # TODO: raise exception for unsupported versions
        version = ".".join(version.split(".")[0:2])
        return XrVersion(version)


class ViCellXRTXTReader:
    data: pd.DataFrame
    series: SeriesData

    def __init__(self, contents: NamedFileContents) -> None:
        self.lines = read_to_lines(contents)
        self.file_info = self._get_file_info()
        self.data = self._read_data()

    def _read_data(self) -> pd.DataFrame:
        # generate long, single column dataframe
        file_data = pd.DataFrame(data=StringIO("\n".join(self.lines)))

        # strip whitespace
        file_data[0] = file_data[0].str.strip()

        # drop empty cells
        file_data = file_data.replace("", None).dropna(axis=0, how="all")

        # split on colon surrounded by any amount of space, limited to one split to avoid destroying datetimes
        file_data = file_data[file_data.columns[0]].str.split(
            r"\s*:\s*", n=1, expand=True
        )

        # pivot the long data of a single sample to a df that is 1 wide row
        file_data["Pivot Index"] = 1
        file_data = file_data.pivot(index="Pivot Index", columns=0)

        # rename the columns to match the existing parser that was based on xls(x) files
        file_data.columns = pd.Index(
            [
                HEADINGS_TO_PARSER_HEADINGS.get(name, name)
                for name in [x[1] for x in file_data.columns]
            ]
        )

        # Do the datetime conversion and remove all rows that fail to pass as datetime
        # This fixes an issue where some files have a hidden invalid first row
        file_data[DATE_HEADER] = pd.to_datetime(
            file_data[DATE_HEADER].astype(str),
            format="%d %b %Y  %I:%M:%S %p",
            errors="coerce",
        )

        return file_data

    def _get_file_info(self) -> SeriesData:
        data = self.lines

        return SeriesData(
            pd.Series(
                [data[0], data[3], data[8]],
                copy=False,
                index=["model", "filepath", "serial"],
            )
        )
