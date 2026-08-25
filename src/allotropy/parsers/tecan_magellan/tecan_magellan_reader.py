import re

import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_excel, split_dataframe
from allotropy.parsers.utils.values import assert_not_none, try_float


class TecanMagellanReader:
    SUPPORTED_EXTENSIONS = "xlsx"
    metadata_lines: list[str]
    measurement_temperatures: dict[str, float]
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        data = read_excel(named_file_contents.contents).replace(np.nan, None)
        data, metadata = split_dataframe(
            data,
            lambda row: row.astype(str).iloc[0].startswith("Date of measurement"),
            include_split_row=True,
        )
        if "Well positions" not in data:
            msg = "File is missing required 'Well positions' column."
            raise AllotropeConversionError(msg)
        self.measurement_temperatures = self._get_measurement_temperatures(data)
        # Files might contain rows with metadata that we will not use, we identify
        # those by checking that the Well positions have the right format
        data = data.dropna(subset=["Well positions"])
        data = data[data["Well positions"].str.match(r"[A-Z]+\d+")]

        # Fill empty plate info if there's a unique value
        if "Plate" in data:
            if len(unique := data["Plate"].dropna().unique()) == 1:
                data["Plate"] = unique[0]

        self.data = data
        self.metadata_lines = assert_not_none(metadata).iloc[:, 0].to_list()

    @staticmethod
    def _get_measurement_temperatures(data: pd.DataFrame) -> dict[str, float]:
        temperatures = {}
        for column in data:
            for value in data[column].dropna():
                if isinstance(value, str) and (
                    match := re.fullmatch(r"(-?[\d.]+)\s*°C", value.strip())
                ):
                    temperatures[str(column)] = try_float(
                        match.group(1), "Measurement temperature"
                    )
                    break
        return temperatures
