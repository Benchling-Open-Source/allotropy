from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd

from allotropy.parsers.utils.uuids import random_uuid_str

# This map is used to coerce the column names coming in the raw data
# into names of the distribution properties.
COLUMN_MAP = {
    "Cumulative Counts/mL": "cumulative_particle_density",
    "Cumulative Count": "cumulative_count",
    "Particle Size(µm)": "particle_size",
    "Differential Counts/mL": "differential_particle_density",
    "Differential Count": "differential_count",
}


VALID_CALCS = ["Average"]


@dataclass(frozen=True, kw_only=True)
class DistributionProperty:
    name: str
    value: float
    distribution_property_id: str


@dataclass(frozen=True, kw_only=True)
class DistributionRow:
    distribution_row_id: str
    properties: list[DistributionProperty]

    def get_property(self, name: str) -> DistributionProperty | None:
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None

    def matches_property_value(
        self, prop_name: str, distribution_row: DistributionRow
    ) -> bool:
        prop = self.get_property(prop_name)
        other_prop = distribution_row.get_property(prop_name)
        if prop and other_prop:
            if prop.value == other_prop.value:
                return True
        return False


@dataclass(frozen=True, kw_only=True)
class Distribution:
    name: str
    data: list[DistributionRow]
    is_calculated: bool
    distribution_id: str

    @staticmethod
    def create(df: pd.DataFrame, name: str, *, is_calculated: bool) -> Distribution:
        data = []
        cols = COLUMN_MAP.values()
        for row in df.index:
            row_data = []
            for col in [x for x in cols if x in df.columns]:
                row_data.append(
                    DistributionProperty(
                        name=col,
                        value=df.loc[row, col],
                        distribution_property_id=random_uuid_str(),
                    )
                )
            data.append(
                DistributionRow(
                    properties=row_data, distribution_row_id=random_uuid_str()
                )
            )
        return Distribution(
            name=name,
            data=data,
            is_calculated=is_calculated,
            distribution_id=random_uuid_str(),
        )


@dataclass(frozen=True, kw_only=True)
class Metadata:
    measurement_time: str
    flush_volume_setting: float
    detector_view_volume: float
    repetition_setting: int
    sample_volume_setting: float
    sample_identifier: str
    dilution_factor_setting: float
    analyst: str
    submitter: str | None = None
    equipment_serial_number: str
    detector_identifier: str
    detector_model_number: str
    software_version: str

    @staticmethod
    def _get_software_version_report_string(report_string: str) -> str:
        match = re.search(r"v(\d+(?:\.\d+)?(?:\.\d+)?)", report_string)
        if match:
            return match.group(1)
        return "Unknown"

    @staticmethod
    def create(df: pd.DataFrame) -> Metadata:
        return Metadata(
            measurement_time=pd.to_datetime(
                str(df.at[8, 5]).replace(".", "-")
            ).isoformat(timespec="microseconds")
            + "Z",
            flush_volume_setting=0,
            detector_view_volume=df.at[9, 5],
            repetition_setting=int(df.at[11, 5]),
            sample_volume_setting=df.at[11, 2],
            sample_identifier=str(df.at[2, 2]),
            dilution_factor_setting=df.at[13, 2],
            analyst=str(df.at[6, 5]),
            submitter=None,
            software_version=Metadata._get_software_version_report_string(df.at[0, 2]),
            equipment_serial_number=str(df.at[4, 5]),
            detector_identifier="",
            detector_model_number=str(df.at[2, 5]),
        )


@dataclass(frozen=True, kw_only=True)
class PharmSpecData:
    metadata: Metadata
    distributions: list[Distribution]

    @staticmethod
    def _get_data_using_key_bounds(
        df: pd.DataFrame, start_key: str, end_key: str
    ) -> pd.DataFrame:
        """Find the data in the raw dataframe. We identify the boundary of the data
        by finding the index first row which contains the word 'Particle' and ending right before
        the index of the first row containing 'Approver'.

        :param df: the raw dataframe
        :param start_key: the key to start the slice
        :parm end_key: the key to end the slice
        :return: the dataframe slice between the stard and end bounds
        """
        start = df[df[1].str.contains(start_key, na=False)].index.values[0]
        end = df[df[0].str.contains(end_key, na=False)].index.values[0] - 1
        return df.loc[start:end, :]

    @staticmethod
    def _extract_data(df: pd.DataFrame) -> pd.DataFrame:
        """Extract the Average data frame from the raw data. Initial use cases have focused on
        only extracting the Average data, not the individual runs. The ASM does support multiple
        Distribution objects, but they don't have names, so it's not possible to pick these out
        after the fact. As such, this extraction only includes the Average data.

        :param df: the raw dataframe
        :return: the average data frame
        """
        data = PharmSpecData._get_data_using_key_bounds(
            df, start_key="Particle", end_key="Approver_"
        )
        data = data.dropna(how="all").dropna(how="all", axis=1)
        data[0] = data[0].ffill()
        data = data.dropna(subset=1).reset_index(drop=True)
        data.columns = pd.Index([x.strip() for x in data.loc[0]])
        data = data.loc[1:, :]
        return data.rename(columns={x: COLUMN_MAP[x] for x in COLUMN_MAP})

    @staticmethod
    def _create_distributions(df: pd.DataFrame) -> list[Distribution]:
        distributions = []
        for g, gdf in df.groupby("Run No."):
            is_calculated = False
            name = str(g)
            if g in VALID_CALCS:
                is_calculated = True
            distribution = Distribution.create(
                df=gdf, name=name, is_calculated=is_calculated
            )
            distributions.append(distribution)
        return distributions

    @staticmethod
    def create(df: pd.DataFrame) -> PharmSpecData:
        data = PharmSpecData._extract_data(df)
        return PharmSpecData(
            metadata=Metadata.create(df),
            distributions=PharmSpecData._create_distributions(data),
        )
