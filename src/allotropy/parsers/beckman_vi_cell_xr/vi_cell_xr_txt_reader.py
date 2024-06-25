from __future__ import annotations

from io import StringIO
import re
from typing import Any

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DATE_HEADER,
    DEFAULT_VERSION,
    MODEL_RE,
    XrVersion,
)
from allotropy.parsers.lines_reader import read_to_lines

HEADINGS_TO_PARSER_HEADINGS = {
    "Dilution": "Dilution factor",
    "Total cells / ml (x 10^6)": "Total cells/ml (x10^6)",
    "Total cells": "Total cells",
    "Average diameter (microns)": "Avg. diam. (microns)",
    "Viable cells": "Viable cells",
    "Average circularity": "Avg. circ.",
    "Viability (%)": "Viability (%)",
    "Total viable cells / ml (x 10^6)": "Viable cells/ml (x10^6)",
    "Sample ID": "Sample ID",
    "Cell type": "Cell type",
}

NUMERIC_COLUMNS = [
    "Dilution factor",
    "Total cells/ml (x10^6)",
    "Total cells",
    "Avg. diam. (microns)",
    "Viable cells",
    "Avg. circ.",
    "Viability (%)",
    "Viable cells/ml (x10^6)",
]


class ViCellXRTXTReader:
    def __init__(self, contents: NamedFileContents) -> None:
        self.lines = read_to_lines(contents)
        self.file_info = self._get_file_info()
        self.file_version = self._get_file_version()
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

        date_header = DATE_HEADER[self.file_version]

        # rename the columns to match the existing parser that was based on xls(x) files
        names = []
        for name in [x[1] for x in file_data.columns]:
            if name == "RunDate":
                newname = date_header
            elif name in HEADINGS_TO_PARSER_HEADINGS:
                newname = HEADINGS_TO_PARSER_HEADINGS[name]
            else:
                newname = name
            names.append(newname)

        file_data.columns = pd.Index(names)

        # convert numeric columns to numeric types
        file_data[NUMERIC_COLUMNS] = file_data[NUMERIC_COLUMNS].astype(float)

        # Do the datetime conversion and remove all rows that fail to pass as datetime
        # This fixes an issue where some files have a hidden invalid first row
        file_data[date_header] = pd.to_datetime(
            file_data[date_header].astype(str),
            format="%d %b %Y  %I:%M:%S %p",
            errors="coerce",
        )

        return file_data

    def _get_file_info(self) -> pd.Series[Any]:
        data = self.lines

        info: pd.Series[Any] = pd.Series(
            [data[0], data[3], data[8]],
            copy=False,
            index=["model", "filepath", "serial"],
        )
        return info

    def _get_file_version(self) -> XrVersion:
        match = re.match(MODEL_RE, self.file_info["model"], flags=re.IGNORECASE)
        try:
            version = match.groupdict()["version"]  # type: ignore[union-attr]
        except AttributeError:
            return DEFAULT_VERSION
        # TODO: raise exception for unsupported versions
        version = ".".join(version.split(".")[0:2])
        return XrVersion(version)
