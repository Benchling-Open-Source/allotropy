from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from allotropy.parsers.roche_cedex_bioht.constants import (
    ANALYTES_LOOKUP,
    DATA_HEADER_V5,
    DATA_HEADER_V6_V7,
    DETECTION_KIT_LOOKUP,
    DETECTION_KIT_RANGE_LOOKUP,
    INFO_HEADER,
    SAMPLE_ROLE_TYPES,
)
from allotropy.parsers.utils.pandas import read_csv, SeriesData
from allotropy.types import IOType


def to_num(data: pd.Series[Any]) -> pd.Series[Any]:
    return pd.to_numeric(data, errors="coerce").replace(np.nan, None)


class RocheCedexBiohtReader:
    SUPPORTED_EXTENSIONS = "txt"
    title_data: SeriesData
    samples_data: pd.DataFrame

    def __init__(self, contents: IOType):
        self.title_data = self.read_title_data(contents)
        self.samples_data = self.read_samples_data(contents)

    def read_title_data(self, contents: IOType) -> SeriesData:
        contents.seek(0)
        return SeriesData(
            read_csv(
                contents,
                delimiter="\t",
                usecols=INFO_HEADER,
                names=INFO_HEADER,
                nrows=1,
            ).T[0]
        )

    def read_samples_data(self, contents: IOType) -> pd.DataFrame:
        software_version = self.title_data[str, "software version"]
        if software_version.startswith("5"):
            data_header = DATA_HEADER_V5
        elif software_version.startswith("6") or software_version.startswith("7"):
            data_header = DATA_HEADER_V6_V7
        else:
            msg = f"Unsupported software version: {software_version}"
            raise ValueError(msg)

        contents.seek(0)
        sample_rows = read_csv(
            contents,
            delimiter="\t",
            usecols=data_header,
            names=data_header,
            skiprows=[0],
        )

        sample_rows = sample_rows.drop_duplicates()

        sample_rows["analyte code"] = sample_rows["analyte name"]
        sample_rows["detection kit"] = sample_rows["analyte name"]
        sample_rows["detection kit range"] = sample_rows["analyte name"]

        sample_rows = sample_rows.replace(
            {
                "analyte name": ANALYTES_LOOKUP,
                "sample role type": SAMPLE_ROLE_TYPES,
                "detection kit": DETECTION_KIT_LOOKUP,
                "detection kit range": DETECTION_KIT_RANGE_LOOKUP,
            }
        )

        if "batch identifier" in sample_rows.columns:
            sample_rows["batch identifier"] = sample_rows["batch identifier"].fillna("")
        else:
            sample_rows["batch identifier"] = [""] * len(sample_rows)

        # concentration values under the test threshold will have a preceding < character
        # this will turn those values into NaN, which is the expected output
        sample_rows["original concentration value"] = sample_rows["concentration value"]
        sample_rows["concentration value"] = to_num(sample_rows["concentration value"])

        return sample_rows
