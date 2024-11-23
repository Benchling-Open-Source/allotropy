from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import ContainerType
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    CalculatedDataItem,
    DataCube,
    DataCubeComponent,
    DataSource,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_absolute_q.constants import (
    AGGREGATION_LOOKUP,
    BRAND_NAME,
    CALCULATED_DATA_REFERENCE,
    CalculatedDataSource,
    DEVICE_TYPE,
    PLATE_WELL_COUNT,
    POSSIBLE_DYE_SETTING_LENGTHS,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
)
from allotropy.parsers.constants import NEGATIVE_ZERO
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


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
    def create(data: SeriesData) -> Group:
        well_identifier = data.get(str, "Well")
        aggregation_type = AGGREGATION_LOOKUP[well_identifier]

        # TODO: if aggregation type is Replicate(Average), check for required columns
        # Raise if column(s) do not exist
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
        data = data[data["Sample"].isna()]
        return map_rows(data, Group.create)


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
    def create(data: SeriesData) -> WellItem:
        return WellItem(
            name=data[str, "Sample"],
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

    @staticmethod
    def create_cube_well_items(well_data: pd.DataFrame) -> list[WellItem]:
        dye_settings = WellItem.get_dye_settings(list(well_data.columns))

        # Order rows by data cube index (this is probably always true, but to be safe).
        well_data = well_data.sort_values("Index", axis="index")
        total_partition_count = well_data["Index"].max()

        # Assume that any dye setting that does not have a '_target' column is the passive dye setting.
        passive_dye_settings = [ds for ds in dye_settings if f"{ds}_target" not in well_data]
        # Assume there is only one passive dye setting.
        if len(passive_dye_settings) != 1:
            msg = f"Expected exactly one possible passive dye setting, got: '{passive_dye_settings}'"
            raise AllotropeConversionError(msg)
        dye_settings -= set(passive_dye_settings)

        cycle_count = DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")
        index_column = well_data["Index"].astype(float).tolist()
        passive_reference_dye_cube = DataCube(
            label="passive reference dye",
            structure_dimensions=cycle_count,
            structure_measures=[
                DataCubeComponent(
                    FieldComponentDatatype.double,
                    "passive reference dye fluorescence",
                    "RFU",
                )
            ],
            dimensions=[index_column],
            measures=[well_data[passive_dye_settings[0]].astype(float).tolist()],
        )

        data = SeriesData(well_data.iloc[0])
        well_items: list[WellItem] = []
        for dye_setting in dye_settings:
            positives_column = f"{dye_setting}_pos"
            if positives_column not in well_data:
                msg = f"Expected {positives_column} column to exist."
                raise AssertionError(msg)
            pos_counts = well_data[positives_column].value_counts()

            well_items.append(WellItem(
                name=data[str, "Sample"],
                measurement_identifier=random_uuid_str(),
                well_identifier=data[str, "Well"],
                plate_identifier=data[str, "Plate"],
                group_identifier=data[str, "Group"],
                target_identifier=data[str, f"{dye_setting}_target"],
                run_identifier=data[str, "Run"],
                instrument_identifier=data[str, "Instrument"],
                timestamp=data[str, "Date"],
                total_partition_count=total_partition_count,
                reporter_dye_setting=dye_setting,
                passive_reference_dye_setting=passive_dye_settings[0],
                flourescence_intensity_threshold_setting=data[float, f"{dye_setting}_threshold"],
                concentration=NEGATIVE_ZERO,
                positive_partition_count=pos_counts[True] if pos_counts else None,
                negative_partition_count=pos_counts[False] if pos_counts else None,
                data_cubes=[
                    DataCube(
                        label="reporter dye",
                        structure_dimensions=cycle_count,
                        structure_measures=[
                            DataCubeComponent(
                                FieldComponentDatatype.double,
                                "reporter dye fluorescence",
                                "RFU",
                            )
                        ],
                        dimensions=[index_column],
                        measures=[well_data[dye_setting].astype(float).tolist()],
                    ),
                    passive_reference_dye_cube,
                ]
            ))

        return well_items



    @staticmethod
    def get_dye_settings(columns: list[str]) -> set[str]:
        return {col for col in columns if len(col) in POSSIBLE_DYE_SETTING_LENGTHS and col == col.upper()}



@dataclass
class Well:
    items: list[WellItem]

    @staticmethod
    def create_wells(data: pd.DataFrame) -> list[Well]:
        data = data.dropna(subset=["Sample"])
        well_groups = [well_data for _, well_data in data.groupby("Well")]
        if "Index" in data:
            return [Well(WellItem.create_cube_well_items(well_data)) for well_data in well_groups]
        else:
            return [Well(map_rows(well_data, WellItem.create)) for well_data in well_groups]


def create_measurement_groups(wells: list[Well]) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(
            experimental_data_identifier=well.items[0].run_identifier,
            plate_well_count=PLATE_WELL_COUNT,
            measurements=[
                Measurement(
                    identifier=item.measurement_identifier,
                    sample_identifier=item.name,
                    location_identifier=item.well_identifier,
                    measurement_time=item.timestamp,
                    plate_identifier=item.plate_identifier,
                    target_identifier=item.target_identifier,
                    total_partition_count=item.total_partition_count,
                    concentration=item.concentration,
                    positive_partition_count=item.positive_partition_count,
                    reporter_dye_setting=item.reporter_dye_setting,
                )
                for item in well.items
            ],
        )
        for well in wells
    ]


def create_calculated_data(
    wells: list[Well], groups: list[Group]
) -> list[CalculatedDataItem]:
    # Map measurement ids to group keys
    group_to_ids = defaultdict(list)
    for well in wells:
        for item in well.items:
            group_to_ids[item.group_key].append(item.measurement_identifier)

    return [
        CalculatedDataItem(
            identifier=calculated_data.identifier,
            name=calculated_data.name,
            value=calculated_data.value,
            unit=calculated_data.unit,
            data_sources=[
                DataSource(source.identifier, source.feature)
                for source in calculated_data.get_data_sources(
                    group_to_ids[group.key], group.calculated_data_ids
                )
            ],
        )
        for group in groups
        for calculated_data in group.calculated_data
    ]


def create_metadata(device_identifier: str, file_path: str) -> Metadata:
    return Metadata(
        device_identifier=device_identifier,
        brand_name=BRAND_NAME,
        device_type=DEVICE_TYPE,
        container_type=ContainerType.well_plate,
        software_name=SOFTWARE_NAME,
        product_manufacturer=PRODUCT_MANUFACTURER,
        file_name=Path(file_path).name,
        unc_path=file_path,
    )
