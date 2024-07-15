from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from allotropy.parsers.appbio_absolute_q.constants import (
    AGGREGATION_LOOKUP,
    CALCULATED_DATA_REFERENCE,
    CalculatedDataSource,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    try_float_from_series,
    try_str_from_series,
    try_str_from_series_or_none,
)


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
    def create(data: pd.Series[str]) -> Group:
        well_identifier = try_str_from_series_or_none(data, "Well")
        aggregation_type = AGGREGATION_LOOKUP[well_identifier]

        calculated_data_items = [
            CalculatedItem(
                random_uuid_str(),
                reference.name,
                try_float_from_series(data, reference.column),
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
            group_identifier=try_str_from_series(data, "Group"),
            target_identifier=try_str_from_series(data, "Target"),
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
    def create(data: pd.Series[str]) -> WellItem:
        return WellItem(
            name=try_str_from_series(data, "Name"),
            measurement_identifier=random_uuid_str(),
            well_identifier=try_str_from_series(data, "Well"),
            plate_identifier=try_str_from_series(data, "Plate"),
            group_identifier=try_str_from_series(data, "Group"),
            target_identifier=try_str_from_series(data, "Target"),
            run_identifier=try_str_from_series(data, "Run"),
            instrument_identifier=try_str_from_series(data, "Instrument"),
            timestamp=try_str_from_series(data, "Date"),
            total_partition_count=round(try_float_from_series(data, "Total")),
            reporter_dye_setting=try_str_from_series(data, "Dye"),
            concentration=try_float_from_series(data, "Conc. cp/uL"),
            positive_partition_count=round(try_float_from_series(data, "Positives")),
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
