from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
import warnings

import pandas as pd

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import ContainerType
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    CalculatedDataItem,
    DataSource,
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_absolute_q.constants import (
    AGGREGATION_LOOKUP,
    AggregationType,
    BRAND_NAME,
    CALCULATED_DATA_REFERENCE,
    CalculatedDataSource,
    CONCENTRATION_COLUMNS,
    DEVICE_TYPE,
    get_dye_settings,
    PLATE_WELL_COUNT,
    POSSIBLE_DYE_SETTING_LENGTHS,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
)
from allotropy.parsers.constants import (
    DEFAULT_EPOCH_TIMESTAMP,
    NEGATIVE_ZERO,
    NOT_APPLICABLE,
)
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
    column: str

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
                DataSource(identifier, source_feature)
                for source_feature in self.source_features
                for identifier in measurement_ids
            ]


def get_calculated_data(
    aggregation_type: AggregationType, data: SeriesData
) -> list[CalculatedItem]:
    # TODO: if aggregation type is Replicate(Average), check for required columns
    # Raise if column(s) do not exist
    return [
        CalculatedItem(
            random_uuid_str(),
            reference.name,
            data[float, reference.column],
            reference.unit,
            reference.source,
            reference.source_features,
            reference.column_key,
        )
        for reference in CALCULATED_DATA_REFERENCE.get(aggregation_type, [])
        if data.get(float, reference.column) is not None
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
        if not self.target_identifier:
            return self.group_identifier
        return f"{self.name}_{self.target_identifier}"

    def get_calculated_data_ids(self) -> dict[str, str]:
        return {
            calculated_data.name: calculated_data.identifier
            for calculated_data in self.calculated_data
        }

    @staticmethod
    def create(data: SeriesData) -> Group:
        well_identifier = data.get(str, "Well")
        calculated_data_items = (
            get_calculated_data(AGGREGATION_LOOKUP[well_identifier], data)
            if well_identifier in AGGREGATION_LOOKUP
            else []
        )
        calculated_data_ids = {
            calculated_data.name: calculated_data.identifier
            for calculated_data in calculated_data_items
        }
        group = Group(
            well_identifier=well_identifier,
            group_identifier=data[str, "Group"],
            target_identifier=data[str, "Target"],
            calculated_data=calculated_data_items,
            calculated_data_ids=calculated_data_ids,
        )
        # discard unread data since it is added to the wells
        data.get_unread()

        return group

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[Group]:
        # If there is no Group column, we expect there to be no calculated data.
        if "Group" not in data:
            return []
        data = data[data["Sample"].isna()]
        return map_rows(data, Group.create)


@dataclass
class WellItem:
    name: str
    measurement_identifier: str
    well_identifier: str
    group_identifier: str
    target_identifier: str
    run_identifier: str
    instrument_identifier: str
    timestamp: str
    total_partition_count: float
    reporter_dye_setting: str
    concentration: float
    positive_partition_count: float
    plate_identifier: str | None = None
    negative_partition_count: float | None = None
    confidence_interval__95__: float | None = None
    passive_reference_dye_setting: str | None = None
    fluorescence_intensity_threshold_setting: float | None = None
    reporter_dye_data_cube: DataCube | None = None
    passive_reference_dye_data_cube: DataCube | None = None
    errors: list[Error] | None = None
    calculated_data: list[CalculatedDataItem] | None = None
    extra_data: dict[str, Any] | None = None

    @property
    def group_key(self) -> str:
        return f"{self.group_identifier}_{self.target_identifier}"

    @staticmethod
    def create(data: SeriesData) -> WellItem:
        measurement_identifier = random_uuid_str()
        return WellItem(
            name=data[str, "Sample"],
            measurement_identifier=measurement_identifier,
            well_identifier=WellItem.get_well_id(data),
            plate_identifier=data.get(str, "Plate"),
            # Group column may be missing if there is no calculated data to group with.
            group_identifier=data.get(str, "Group", ""),
            target_identifier=data.get(str, "Target", NOT_APPLICABLE),
            run_identifier=data[str, "Run"],
            instrument_identifier=data.get(str, "Instrument", NOT_APPLICABLE),
            timestamp=data.get(str, "Date", DEFAULT_EPOCH_TIMESTAMP),
            total_partition_count=round(data[float, "Total"]),
            reporter_dye_setting=data[str, ("Dye", "Channels")],
            concentration=data[float, CONCENTRATION_COLUMNS],
            positive_partition_count=round(data[float, ("Positives", "Count")]),
            confidence_interval__95__=data.get(float, "95%CI"),
            fluorescence_intensity_threshold_setting=data.get(float, "Threshold"),
            calculated_data=[
                CalculatedDataItem(
                    identifier=calc_data.identifier,
                    name=calc_data.name,
                    value=calc_data.value,
                    unit=calc_data.unit,
                    data_sources=calc_data.get_data_sources(
                        [measurement_identifier], {}
                    ),
                )
                for calc_data in get_calculated_data(AggregationType.INDIVIDUAL, data)
            ],
            extra_data=data.get_unread(),
        )

    @staticmethod
    def create_cube_well_items(well_data: pd.DataFrame) -> list[WellItem]:
        dye_settings = get_dye_settings(list(well_data.columns))

        # Order rows by data cube index (this is probably always true, but to be safe).
        well_data = well_data.sort_values("Index", axis="index")
        total_partition_count = float(well_data["Index"].max())

        # Assume that any dye setting that does not have a '_target' column is the passive dye setting.
        passive_dye_settings = [
            ds for ds in dye_settings if f"{ds}_target" not in well_data
        ]
        # Assume there is only one passive dye setting.
        if len(passive_dye_settings) != 1:
            msg = f"Expected exactly one possible passive dye setting, got: '{passive_dye_settings}'"
            raise AllotropeConversionError(msg)

        cycle_count = DataCubeComponent(
            FieldComponentDatatype.integer, "cycle count", "#"
        )
        index_column = well_data["Index"].astype(float).tolist()

        data = SeriesData(well_data.iloc[0])
        well_items: list[WellItem] = []
        for dye_setting in [ds for ds in dye_settings if f"{ds}_target" in well_data]:
            positives_column = f"{dye_setting}_pos"
            if positives_column not in well_data:
                msg = f"Expected {positives_column} column to exist."
                raise AllotropeConversionError(msg)
            pos_counts = well_data[positives_column].value_counts().to_dict()
            positive_partition_count = float(pos_counts.get(True, 0))
            negative_partition_count = float(pos_counts.get(False, 0))
            if (
                positive_partition_count + negative_partition_count
            ) != total_partition_count:
                msg = f"positive partition count ({positive_partition_count}) + negative partition count ({negative_partition_count}) != total partition count ({total_partition_count}). This probably means the values in '{positives_column}' are not bools as expected."
                warnings.warn(
                    msg,
                    stacklevel=2,
                )
            concentration = data.get(float, CONCENTRATION_COLUMNS)
            errors = []
            if concentration is None:
                concentration = NEGATIVE_ZERO
                errors.append(Error(error="N/A", error_feature="number concentration"))

            well_items.append(
                WellItem(
                    name=data[str, "Sample"],
                    measurement_identifier=random_uuid_str(),
                    well_identifier=data[str, "Well"],
                    plate_identifier=data.get(str, "Plate"),
                    group_identifier=data.get(str, "Group", ""),
                    target_identifier=data[str, f"{dye_setting}_target"],
                    run_identifier=data[str, "Run"],
                    instrument_identifier=data.get(str, "Instrument", NOT_APPLICABLE),
                    timestamp=data.get(str, "Date", DEFAULT_EPOCH_TIMESTAMP),
                    total_partition_count=total_partition_count,
                    reporter_dye_setting=dye_setting,
                    passive_reference_dye_setting=passive_dye_settings[0],
                    fluorescence_intensity_threshold_setting=data[
                        float, f"{dye_setting}_threshold"
                    ],
                    concentration=concentration,
                    positive_partition_count=positive_partition_count,
                    negative_partition_count=negative_partition_count,
                    confidence_interval__95__=data.get(float, "95%CI"),
                    reporter_dye_data_cube=DataCube(
                        label="reporter dye",
                        structure_dimensions=[cycle_count],
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
                    passive_reference_dye_data_cube=DataCube(
                        label="passive reference dye",
                        structure_dimensions=[cycle_count],
                        structure_measures=[
                            DataCubeComponent(
                                FieldComponentDatatype.double,
                                "passive reference dye fluorescence",
                                "RFU",
                            )
                        ],
                        dimensions=[index_column],
                        measures=[
                            well_data[passive_dye_settings[0]].astype(float).tolist()
                        ],
                    ),
                    errors=errors,
                    extra_data=data.get_unread(
                        # Skip data cube fields
                        skip={
                            "FAM",
                            "VIC",
                            "ABY",
                            "JUN",
                            "ROX",
                            "Index",
                            "FAM_pos",
                            "VIC_pos",
                            "ABY_pos",
                            "JUN_pos",
                            "FAM_target",
                            "VIC_target",
                            "ABY_target",
                            "JUN_target",
                            "FAM_threshold",
                            "VIC_threshold",
                            "ABY_threshold",
                            "JUN_threshold",
                        }
                    ),
                )
            )

        return well_items

    @staticmethod
    def get_dye_settings(columns: list[str]) -> list[str]:
        return [
            col
            for col in columns
            if len(col) in POSSIBLE_DYE_SETTING_LENGTHS and col == col.upper()
        ]

    @staticmethod
    def get_well_id(data: SeriesData) -> str:
        if well_id := data.get(str, "Well", ""):
            return well_id

        sample_name = data[str, "Sample"]
        if match := re.match(r"Sample ([a-zA-Z0-9]+)", sample_name):
            return match.groups()[0]
        msg = f"Unable to get well identifier from sample {sample_name}"
        raise AllotropeConversionError(msg)


@dataclass
class Well:
    items: list[WellItem]

    @staticmethod
    def create_wells(data: pd.DataFrame) -> list[Well]:
        if "Channels" in data:
            subset_col = "Channels"
            groupby_col = "Sample"
        else:
            subset_col = "Sample"
            groupby_col = "Well"
        data = data.dropna(subset=[subset_col])

        well_groups = [well_data for _, well_data in data.groupby(groupby_col)]
        if "Index" in data:
            return [
                Well(WellItem.create_cube_well_items(well_data))
                for well_data in well_groups
            ]
        else:
            return [
                Well(map_rows(well_data, WellItem.create)) for well_data in well_groups
            ]


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
                    negative_partition_count=item.negative_partition_count,
                    confidence_interval__95__=item.confidence_interval__95__,
                    reporter_dye_setting=item.reporter_dye_setting,
                    passive_reference_dye_setting=item.passive_reference_dye_setting,
                    fluorescence_intensity_threshold_setting=item.fluorescence_intensity_threshold_setting,
                    reporter_dye_data_cube=item.reporter_dye_data_cube,
                    passive_reference_dye_data_cube=item.passive_reference_dye_data_cube,
                    errors=item.errors,
                    custom_info=item.extra_data,
                )
                for item in well.items
            ],
        )
        for well in wells
    ]


def create_calculated_data(
    wells: list[Well], groups: list[Group], common_columns: list[str]
) -> list[CalculatedDataItem]:
    if not groups:
        return []
    # Map measurement ids to group keys and get per-measurement calculated data items
    group_to_ids = defaultdict(list)
    calculated_data_items: list[CalculatedDataItem] = []
    for well in wells:
        for item in well.items:
            group_to_ids[item.group_key].append(item.measurement_identifier)
            group_to_ids[item.group_identifier].append(item.measurement_identifier)
            calculated_data_items.extend(item.calculated_data or [])

    # When parsing a "Summary" file, some calculated columns are across all samples in a group, while others
    # are across a (group, target) pair. common_columns tells us which columns are across the group.
    # For these "common columns" extract them from (group, target) groups into (group,) only groups, so that
    # they are attributed correctly and not duplicated.
    group_id_to_group: dict[str, Group] = {}
    summary_calculated_data: defaultdict[str, dict[str, CalculatedItem]] = defaultdict(
        dict
    )
    for group in groups:
        group_id_to_group[group.group_identifier] = group
        pruned: list[CalculatedItem] = []
        for calculated_data in group.calculated_data:
            if calculated_data.column in common_columns:
                existing_entry = summary_calculated_data.get(
                    group.group_identifier, {}
                ).get(calculated_data.column)
                if existing_entry and existing_entry.value != calculated_data.value:
                    msg = f"Mismatch in value within group for summary calculated data column: '{calculated_data.column}': '{existing_entry.value}' vs '{calculated_data.value}'"
                    raise AllotropeConversionError(msg)
                summary_calculated_data[group.group_identifier][
                    calculated_data.column
                ] = calculated_data
            else:
                pruned.append(calculated_data)
        group.calculated_data = pruned

    for group_id, calc_column_to_calc_data in summary_calculated_data.items():
        groups.append(
            Group(
                well_identifier=group_id_to_group[group_id].well_identifier,
                group_identifier=group_id,
                target_identifier="",
                calculated_data=list(calc_column_to_calc_data.values()),
                calculated_data_ids=group_id_to_group[group_id].calculated_data_ids,
            )
        )

    calculated_data_items.extend(
        [
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
    )
    return calculated_data_items


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
