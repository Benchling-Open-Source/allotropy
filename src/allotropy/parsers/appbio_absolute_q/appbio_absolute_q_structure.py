from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from allotropy.parsers.appbio_absolute_q.constants import (
    AGGREGATION_LOOKUP,
    CALCULATED_DATA_REFERENCE,
    CalculatedDataSource,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass
class DataSource:
    identifier: str
    feature: str


@dataclass
class CalculatedItem:
    identifier: str
    name: str
    value: float
    unit: str
    source: CalculatedDataSource
    source_features: list[str]

    def get_data_sources(
        self, measurement_ids: list[str], calculated_data_ids: dict[str, str]
    ) -> list[DataSource]:
        if self.source == CalculatedDataSource.CALCULATED_DATA:
            return [
                DataSource(calculated_data_ids[source_feature], source_feature)
                for source_feature in self.source_features
            ]
        else:
            return [
                DataSource(identifier, self.source_features[0])
                for identifier in measurement_ids
            ]


@dataclass
class Group:
    well_identifier: str | None
    group_identifier: str
    target_identifier: str
    calculated_data: list[CalculatedItem]
    calculated_data_ids: dict[str, str]

    @property
    def name(self) -> str:
        return self.group_identifier.split("(")[0].strip()

    @property
    def key(self) -> str:
        return f"{self.name}_{self.target_identifier}"

    def get_calculated_data_ids(self) -> dict[str, str]:
        return {
            calculated_data.name: calculated_data.identifier
            for calculated_data in self.calculated_data
        }

    @staticmethod
    def create(series: pd.Series[str]) -> Group:
        data = SeriesData(series)
        well_identifier = data.get(str, "Well")
        aggregation_type = AGGREGATION_LOOKUP[well_identifier]

        calculated_data_items = [
            CalculatedItem(
                random_uuid_str(),
                reference.name,
                data[float, reference.column],
                reference.unit,
                reference.source,
                reference.source_features,
            )
            for reference in CALCULATED_DATA_REFERENCE.get(aggregation_type, [])
        ]
        calculated_data_ids = {
            calculated_data.name: calculated_data.identifier
            for calculated_data in calculated_data_items
        }
        return Group(
            well_identifier=well_identifier,
            group_identifier=data[str, "Group"],
            target_identifier=data[str, "Target"],
            calculated_data=calculated_data_items,
            calculated_data_ids=calculated_data_ids,
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[Group]:
        data = data.replace(np.nan, None)[data["Name"].isna()]
        return [Group.create(row_data) for _, row_data in data.iterrows()]


@dataclass
class WellItem:
    name: str
    measurement_identifier: str
    well_identifier: str
    plate_identifier: str
    group_identifier: str
    target_identifier: str
    run_identifier: str
    instrument_identifier: str
    timestamp: str
    total_partition_count: float
    reporter_dye_setting: str
    concentration: float
    positive_partition_count: float

    @property
    def group_key(self) -> str:
        return f"{self.group_identifier}_{self.target_identifier}"

    @staticmethod
    def create(series: pd.Series[str]) -> WellItem:
        data = SeriesData(series)
        return WellItem(
            name=data[str, "Name"],
            measurement_identifier=random_uuid_str(),
            well_identifier=data[str, "Well"],
            plate_identifier=data[str, "Plate"],
            group_identifier=data[str, "Group"],
            target_identifier=data[str, "Target"],
            run_identifier=data[str, "Run"],
            instrument_identifier=data[str, "Instrument"],
            timestamp=data[str, "Date"],
            total_partition_count=round(data[float, "Total"]),
            reporter_dye_setting=data[str, "Dye"],
            concentration=data[float, "Conc. cp/uL"],
            positive_partition_count=round(data[float, "Positives"]),
        )


@dataclass
class Well:
    items: list[WellItem]

    @staticmethod
    def create_wells(data: pd.DataFrame) -> list[Well]:
        data = data.dropna(subset=["Name"]).replace(np.nan, None)
        return [
            Well(list(well_data.apply(WellItem.create, axis="columns")))  # type: ignore[call-overload]
            for _, well_data in data.groupby("Well")
        ]
