from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.parsers.constants import DEFAULT_EPOCH_TIMESTAMP, NOT_APPLICABLE
from allotropy.parsers.msd_workbench.constants import (
    LUMINESCENCE,
    LUMINESCENCE_DETECTOR,
    SAMPLE_ROLE_TYPE_MAPPING,
    SOFTWARE_NAME,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass(frozen=True)
class Header:
    file_name: str
    name: str
    model: str

    @staticmethod
    def create(file_name: str) -> Header:
        return Header(
            file_name=file_name,
            model=NOT_APPLICABLE,
            name=SOFTWARE_NAME,
        )


@dataclass(frozen=True)
class PlateData:
    measurement_time: str
    plate_well_count: int
    well_plate_id: str
    well_data: list[WellData]

    @staticmethod
    def create(
        data: pd.DataFrame,
    ) -> PlateData:
        first_row = str(data.iloc[0, 0])
        well_plate_id = first_row.split("_")[-1].strip()
        data = data.iloc[1:].reset_index(drop=True)
        # Set the first row as the header
        data.columns = pd.Index(data.iloc[0])
        data = data[1:].reset_index(drop=True)
        well_data = []
        for _row_index, row in data.iterrows():
            row_series = SeriesData(row)
            well_data.append(
                WellData.create(
                    luminescence=row_series[int, "Signal"],
                    location_id=row_series[str, "Well"] + "_" + row_series[str, "Spot"],
                    sample_id=row_series[str, "Sample"] + "_" + row_series[str, "Well"],
                    concentration=row_series[float, "Concentration"],
                    measurement_custom_info={
                        "detection range": row_series.get(str, "Detection Range"),
                        "assay identifier": row_series.get(str, "Assay"),
                    },
                    dilution_factor=row_series.get(int, "Dilution Factor"),
                )
            )

        well_column = data["Well"]
        plate_well_count = len(well_column.unique())

        return PlateData(
            measurement_time=DEFAULT_EPOCH_TIMESTAMP,
            well_plate_id=well_plate_id,
            plate_well_count=plate_well_count,
            well_data=well_data,
        )


@dataclass(frozen=True)
class WellData:
    luminescence: int
    location_identifier: str
    sample_identifier: str
    sample_role_type: SampleRoleType | None
    mass_concentration: float | None
    dilution_factor: int | None = None
    measurement_custom_info: dict[str, Any] | None = None

    @staticmethod
    def create(
        luminescence: int,
        location_id: str,
        sample_id: str,
        concentration: float | None = None,
        measurement_custom_info: dict[str, Any] | None = None,
        dilution_factor: int | None = None,
    ) -> WellData:
        return WellData(
            luminescence=luminescence,
            location_identifier=location_id,
            sample_identifier=sample_id,
            sample_role_type=SAMPLE_ROLE_TYPE_MAPPING.get(sample_id[0].lower()),
            mass_concentration=concentration,
            measurement_custom_info=measurement_custom_info,
            dilution_factor=dilution_factor,
        )


def create_metadata(header: Header) -> Metadata:
    asm_file_identifier = Path(header.file_name).with_suffix(".json")
    return Metadata(
        file_name=header.file_name.rsplit("\\", 1)[-1],
        unc_path=header.file_name,
        software_name=header.name,
        device_identifier=NOT_APPLICABLE,
        model_number=header.model,
        asm_file_identifier=asm_file_identifier.name,
        data_system_instance_id=NOT_APPLICABLE,
    )


def create_measurement_groups(plate_data: PlateData) -> list[MeasurementGroup]:
    grouped_wells = defaultdict(list)

    for well in plate_data.well_data:
        assay_id = (
            well.measurement_custom_info.get("assay identifier")
            if well.measurement_custom_info
            else None
        )
        grouped_wells[assay_id].append(well)

    well_data: list[list[WellData]] = list(grouped_wells.values())

    return [
        MeasurementGroup(
            measurement_time=plate_data.measurement_time,
            plate_well_count=plate_data.plate_well_count,
            measurements=[
                Measurement(
                    type_=MeasurementType.LUMINESCENCE,
                    identifier=random_uuid_str(),
                    luminescence=well.luminescence,
                    sample_identifier=well.sample_identifier,
                    location_identifier=well.location_identifier,
                    well_plate_identifier=plate_data.well_plate_id,
                    device_type=LUMINESCENCE_DETECTOR,
                    detection_type=LUMINESCENCE,
                    mass_concentration=well.mass_concentration,
                    sample_role_type=well.sample_role_type,
                    measurement_custom_info=well.measurement_custom_info,
                    sample_custom_info={
                        "dilution factor setting": well.dilution_factor,
                    },
                )
                for well in well_group
            ],
        )
        for well_group in well_data
    ]
