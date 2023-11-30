from __future__ import annotations

from io import IOBase
import re
from typing import Any

import pandas as pd

from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DATE_HEADER,
    DEFAULT_VERSION,
    MODEL_RE,
    XrVersion,
)


class ViCellXRReader:
    def __init__(self, contents: IOBase) -> None:
        self.contents = contents
        self.file_info = self._get_file_info()
        self.file_version = self._get_file_version()
        self.data = self._read_data()

    def _read_data(self) -> pd.DataFrame:
        header_row = 4
        if self.file_version == XrVersion._2_04:
            header_row = 3

        header = self._get_file_header(header_row)
        skiprows = header_row + 1
        file_data: pd.DataFrame = pd.read_excel(
            self.contents,
            skiprows=skiprows,
            names=header,
            parse_dates=[DATE_HEADER[self.file_version]],
            date_format="%d %b %Y  %I:%M:%S %p",
        )
        return file_data

    def _get_file_header(self, header_row: int) -> list[str]:
        """Combine the two rows that forms the header."""
        header = pd.read_excel(
            self.contents,
            nrows=2,
            skiprows=header_row,
            header=None,
        ).fillna("")

        header_list: list[str] = header.agg(
            lambda x: " ".join(x).replace(" /ml", "/ml").strip()
        ).to_list()
        return header_list

    def _get_file_info(self) -> pd.Series[Any]:
        info: pd.Series[Any] = pd.read_excel(
            self.contents, nrows=3, header=None, usecols=[0]
        ).squeeze()
        info.index = pd.Index(["model", "filepath", "serial"])
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
