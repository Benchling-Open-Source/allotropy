from __future__ import annotations

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.luminex_xponent.luminex_xponent_reader import (
    LuminexXponentReader,
)


class LuminexIntelliflexReader:
    SUPPORTED_EXTENSIONS = LuminexXponentReader.SUPPORTED_EXTENSIONS

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        # Use the xPONENT reader as the underlying implementation
        self._xponent_reader = LuminexXponentReader(named_file_contents)

    @property
    def header_data(self) -> pd.DataFrame:
        return self._xponent_reader.header_data

    @property
    def calibration_data(self) -> pd.DataFrame:
        return self._xponent_reader.calibration_data

    @property
    def minimum_assay_bead_count_setting(self) -> float | None:
        return self._xponent_reader.minimum_assay_bead_count_setting

    @property
    def results_data(self) -> dict[str, pd.DataFrame]:
        return self._xponent_reader.results_data

    @classmethod
    def read(cls, named_file_contents: NamedFileContents) -> LuminexIntelliflexReader:
        return cls(named_file_contents)
