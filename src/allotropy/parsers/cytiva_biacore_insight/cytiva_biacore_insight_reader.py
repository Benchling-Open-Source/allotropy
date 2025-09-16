from __future__ import annotations

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_multisheet_excel

REQUIRED_SHEETS = ("Properties", "Report point table", "Evaluation - Kinetics")


class CytivaBiacoreInsightReader:
    SUPPORTED_EXTENSIONS = "xlsx, xlsm"
    data: dict[str, pd.DataFrame]

    @staticmethod
    def create(named_file_contents: NamedFileContents) -> CytivaBiacoreInsightReader:
        data = read_multisheet_excel(
            named_file_contents.contents,
            header=None,
            engine="calamine",
        )
        if missing_sheets := [sheet for sheet in REQUIRED_SHEETS if sheet not in data]:
            msg = f"Missing required sheets: {', '.join(missing_sheets)}"
            raise AllotropeConversionError(msg)

        return CytivaBiacoreInsightReader(data)

    def __init__(self, data: dict[str, pd.DataFrame]) -> None:
        self.data = data
