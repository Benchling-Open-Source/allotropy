from __future__ import annotations

from io import StringIO

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DATE_HEADER,
    HEADINGS_TO_PARSER_HEADINGS,
)
from allotropy.parsers.lines_reader import read_to_lines
from allotropy.parsers.utils.pandas import SeriesData


class ViCellXRTXTReader:
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
