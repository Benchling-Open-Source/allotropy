import io

import numpy as np
import pandas as pd


def convert_datetime(x: pd.Series) -> pd.Series:
    return pd.to_datetime(x).dt.strftime("%Y-%m-%d %H:%M:%S")


def convert_float(x: pd.Series) -> pd.Series:
    return pd.to_numeric(x, errors="coerce")


def convert_int(x: pd.Series) -> pd.Series:
    return pd.to_numeric(x, errors="coerce")


def convert_string(x: pd.Series) -> pd.Series:
    return x.astype(str)


conversors = {
    np.datetime64: convert_datetime,
    np.float64: convert_float,
    np.int64: convert_int,
    np.dtypes.ObjectDType: convert_string,
}


desired_columns = {
    "Analysis by": np.dtypes.ObjectDType,
    "Sample ID": np.dtypes.ObjectDType,
    "Minimum Diameter (μm)": np.float64,
    "Maximum Diameter (μm)": np.float64,
    "Analysis date/time": np.datetime64,
    "Cell type": np.dtypes.ObjectDType,
    "Dilution": np.float64,
    "Viability (%)": np.float64,
    "Total (x10^6) cells/mL": np.float64,
    "Viable (x10^6) cells/mL": np.float64,
    "Average diameter (μm)": np.float64,
    "Average viable diameter (μm)": np.float64,
    "Cell count": np.int64,
    "Viable cells": np.int64,
    "Average circularity": np.float64,
    "Average viable circularity": np.float64,
}


class ViCellBluReader:
    @classmethod
    def read(cls, contents: io.IOBase) -> pd.DataFrame:
        raw_data = pd.read_csv(contents, index_col=False)  # type: ignore[call-overload]

        columns: list[pd.Series] = []
        for column, desired_type in desired_columns.items():
            col = raw_data.get(column)
            if not isinstance(col, pd.Series):
                continue

            new_col = (
                col if col.dtype == desired_type else conversors[desired_type](col)
            )
            columns.append(new_col)

        return pd.concat(columns, axis=1).replace(np.nan, None)
