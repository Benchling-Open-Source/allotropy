from __future__ import annotations

import re
from typing import Any

import pandas as pd

from allotropy.allotrope.pandas_util import read_excel
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DATE_HEADER,
    DEFAULT_VERSION,
    MODEL_RE,
    XrVersion,
)
from allotropy.types import IOType


class ViCellXRReader:
    def __init__(self, contents: IOType) -> None:
        self.contents = contents
        self.file_info = self._get_file_info()
        self.file_version = self._get_file_version()
        self.data = self._read_data()

    def _read_excel(self, **kwargs: Any) -> pd.DataFrame:
        return read_excel(self.contents, **kwargs)

    def _read_data(self) -> pd.DataFrame:
        header_row = 4
        if self.file_version == XrVersion._2_04:
            header_row = 3

        header = self._get_file_header(header_row)
        skiprows = header_row + 1
        date_header = DATE_HEADER[self.file_version]

        file_data = self._read_excel(skiprows=skiprows, names=header)

        # Do the datetime conversion and remove all rows that fail to pass as datetime
        # This fixes an issue where some files have a hidden invalid first row
        file_data[date_header] = pd.to_datetime(
            file_data[date_header], format="%d %b %Y  %I:%M:%S %p", errors="coerce"
        )
        file_data = file_data.dropna(subset=date_header)

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

    def _get_file_info(self) -> pd.Series[Any]:
        info: pd.Series[Any] = self._read_excel(
            nrows=3, header=None, usecols=[0]
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
