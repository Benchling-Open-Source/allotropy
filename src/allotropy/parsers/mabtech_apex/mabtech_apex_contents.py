from __future__ import annotations

import numpy as np
import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_multisheet_excel, SeriesData
from allotropy.parsers.utils.values import assert_not_none


class MabtechApexContents:
    @staticmethod
    def create(named_file_contents: NamedFileContents) -> MabtechApexContents:
        raw_contents = read_multisheet_excel(named_file_contents.contents)
        return MabtechApexContents(raw_contents)

    def __init__(self, raw_contents: dict[str, pd.DataFrame]) -> None:
        contents = {
            str(name): df.replace(np.nan, None) for name, df in raw_contents.items()
        }

        self.plate_info = self._get_plate_info(contents)
        self.data = self._get_data(contents)

    def _get_plate_info(self, contents: dict[str, pd.DataFrame]) -> SeriesData:
        sheet = assert_not_none(
            contents.get("Plate Information"),
            msg="Unable to find 'Plate Information' sheet.",
        ).dropna(axis="columns", how="all")

        data = {}
        for _, * (title, value, *_) in sheet.itertuples():
            if title is None:
                break
            data[str(title)] = None if value is None else str(value)

        return SeriesData(pd.Series(data))

    def _get_data(self, contents: dict[str, pd.DataFrame]) -> pd.DataFrame:
        sheet = assert_not_none(
            contents.get("Plate Database"), msg="Unable to find 'Plate Database' sheet."
        )

        return sheet.dropna(axis="columns", how="all")
