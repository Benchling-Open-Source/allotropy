from __future__ import annotations

import numpy as np
import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    parse_header_row,
    read_multisheet_excel,
    SeriesData,
)
from allotropy.parsers.utils.values import assert_not_none


class MabtechApexReader:
    SUPPORTED_EXTENSIONS = "xlsx"

    plate_info: SeriesData
    data: pd.DataFrame

    @staticmethod
    def create(named_file_contents: NamedFileContents) -> MabtechApexReader:
        raw_contents = read_multisheet_excel(named_file_contents.contents)
        return MabtechApexReader(raw_contents)

    def __init__(self, raw_contents: dict[str, pd.DataFrame]) -> None:
        contents = {
            str(name): df.replace(np.nan, None) for name, df in raw_contents.items()
        }

        self.plate_info = self._get_plate_info(contents)
        self.data = self._get_data(contents)

    def _get_plate_info(self, contents: dict[str, pd.DataFrame]) -> SeriesData:
        sheet = (
            assert_not_none(
                contents.get("Plate Information"),
                msg="Unable to find 'Plate Information' sheet.",
            )
            .dropna(axis=1, how="all")
            .T
        )
        sheet.iloc[0] = sheet.iloc[0].apply(lambda x: x.replace(":", "", 1))
        return df_to_series_data(parse_header_row(sheet))

    def _get_data(self, contents: dict[str, pd.DataFrame]) -> pd.DataFrame:
        sheet = assert_not_none(
            contents.get("Plate Database"), msg="Unable to find 'Plate Database' sheet."
        )

        return sheet.dropna(axis="columns", how="all")
