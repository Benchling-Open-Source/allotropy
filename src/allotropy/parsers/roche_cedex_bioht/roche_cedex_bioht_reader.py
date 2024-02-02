from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.parsers.roche_cedex_bioht.constants import (
    ANALYTES_LOOKUP,
    DATA_HEADER,
    INFO_HEADER,
    SAMPLE_ROLE_TYPES,
)
from allotropy.types import IOType


def to_num(data: pd.Series[Any]) -> pd.Series[Any]:
    return pd.to_numeric(data, errors="coerce").replace(np.nan, None)


class RocheCedexBiohtReader:
    def __init__(self, contents: IOType):
        self.title_data = self.read_title_data(contents)
        self.samples_data = self.read_samples_data(contents)

    def read_title_data(self, contents: IOType) -> pd.Series[Any]:
        contents.seek(0)
        return read_csv(
            contents,
            delimiter="\t",
            usecols=INFO_HEADER,
            names=INFO_HEADER,
            nrows=1,
        ).T[0]

    def read_samples_data(self, contents: IOType) -> pd.DataFrame:
        contents.seek(0)
        sample_rows = read_csv(
            contents,
            delimiter="\t",
            usecols=DATA_HEADER,
            names=DATA_HEADER,
            skiprows=[0],
        )

        sample_rows = sample_rows.replace(
            {"analyte name": ANALYTES_LOOKUP, "sample role type": SAMPLE_ROLE_TYPES}
        )

        sample_rows["batch identifier"] = sample_rows["batch identifier"].fillna("")

        # concentration values under the test threshold will have a preceding < character
        # this will turn those values into NaN, which is the expected output
        sample_rows["concentration value"] = to_num(sample_rows["concentration value"])

        return sample_rows
