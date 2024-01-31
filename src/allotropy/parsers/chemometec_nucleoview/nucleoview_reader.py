import pandas as pd

from allotropy.allotrope.pandas_util import read_csv
from allotropy.types import IOType


class NucleoviewReader:
    @classmethod
    def read(cls, contents: IOType) -> pd.DataFrame:
        df = read_csv(
            contents,
            skipfooter=1,
            sep=";",
            usecols=[0, 1],
            skipinitialspace=True,
            index_col=False,
        ).dropna(axis=0, how="all")

        # add a common index to all rows for our group by and pivot
        df["group_by"] = ["Group1"] * len(df)

        # pivot to wide format
        raw_data = df.pivot(
            index="group_by", columns=df.columns[0], values=df.columns[1]
        )

        # give timezone offset a positive symbol if not present
        if "Time zone offset" in raw_data.columns and "Date time" in raw_data.columns:
            raw_data.loc[
                ~raw_data["Time zone offset"].str.startswith("-"), "Time zone offset"
            ] = ("+" + raw_data["Time zone offset"])

            # combine date time and UTC offset
            raw_data["datetime"] = pd.to_datetime(
                raw_data["Date time"] + raw_data["Time zone offset"]
            )
        raw_data["Sample ID"] = raw_data["Image"].str.split("-", n=3).str[3]
        raw_data = raw_data.rename(
            {"Estimated cell diameter [um]": "Estimated cell diameter (um)"},
            axis=1,
        )

        return raw_data
