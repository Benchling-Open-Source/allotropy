import io
from typing import cast

import pandas as pd


class NucleoviewReader:
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
        if "Time zone offset" in raw_data.columns and "Date time" in raw_data.columns:
            raw_data.loc[
                ~raw_data["Time zone offset"].str.startswith("-"), "Time zone offset"
            ] = ("+" + raw_data["Time zone offset"])

            # combine date time and UTC offset
            raw_data["datetime"] = pd.to_datetime(
                raw_data["Date time"] + raw_data["Time zone offset"]
            )

        return cast(pd.DataFrame, raw_data)
