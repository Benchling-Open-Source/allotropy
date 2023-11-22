import io

import numpy as np
import pandas as pd


def convert_datetime(x: pd.Series) -> pd.Series:
    return pd.to_datetime(x).dt.strftime("%Y-%m-%d %H:%M:%S%z")


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
    "Image": np.dtypes.ObjectDType,
    "Operator": np.dtypes.ObjectDType,
    "Viability (%)": np.float64,
    "Live (cells/ml)": np.float64,
    "Dead (cells/ml)": np.float64,
    "Total (cells/ml)": np.float64,
    "Estimated cell diameter (um)": np.float64,
    "Cell diameter standard deviation (um)": np.float64,
    "(%) of cells in aggregates with five or more cells": np.float64,
    "Sample Volume (ul)": np.float64,
    "Dilution Volume (ul)": np.float64,
    "Multiplication factor": np.float64,
    "cm filename": np.dtypes.ObjectDType,
    "Protocol template title": np.dtypes.ObjectDType,
    "Protocol template purpose": np.dtypes.ObjectDType,
    "Protocol template filename": np.dtypes.ObjectDType,
    "Protocol adaptation title": np.dtypes.ObjectDType,
    "Protocol adaptation purpose": np.dtypes.ObjectDType,
    "Protocol adaptation filename": np.dtypes.ObjectDType,
    "Instrument type": np.dtypes.ObjectDType,
    "Instrument s/n": np.dtypes.ObjectDType,
    "datetime": np.datetime64,
    "Login ID": np.dtypes.ObjectDType,
    "PC": np.dtypes.ObjectDType,
    "Application SW version": np.dtypes.ObjectDType,
    "21 CFR Part 11": np.dtypes.ObjectDType,
    "Event log format": np.dtypes.ObjectDType,
    "csv file version": np.dtypes.ObjectDType,
}


class NC200Reader:
    @classmethod
    def read(cls, contents: io.IOBase) -> pd.DataFrame:
        df = pd.read_csv(contents, skipfooter=1, sep=";", index_col=False)  # type: ignore[call-overload]

        # drop last column
        df = df.drop(df.columns[2], axis=1)

        # drop NA and blank values in our key column
        df = df[df[df.columns[1]].notna()]
        df = df[df[df.columns[1]] != " "]

        # add a common index to all rows for our group by and pivot
        df.index = [0] * len(df)

        # pivot to wide format
        raw_data = df.pivot(columns=df.columns[0], values=df.columns[1])

        # give timezone offset a positive symbol if not present
        raw_data.loc[
            ~raw_data["Time zone offset"].str.startswith("-"), "Time zone offset"
        ] = ("+" + raw_data["Time zone offset"])

        # combine date time and UTC offset
        raw_data["datetime"] = pd.to_datetime(
            raw_data["Date time"] + raw_data["Time zone offset"]
        )

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
