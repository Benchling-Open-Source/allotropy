from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.methodical_mind import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass(frozen=True)
class Header:
    file_name: str
    version: str
    model: str
    serial_number: str

    @staticmethod
    def create(data: SeriesData) -> Header:
        return Header(
            file_name=data[str, "FileName"],
            version=data[str, "Version"],
            model=data[str, "Model"],
            serial_number=data[str, "Serial #"],
        )


@dataclass(frozen=True)
class PlateData:
    measurement_time: str
    plate_well_count: int
    analyst: str | None
    well_plate_id: str
    well_data: list[WellData]

    @staticmethod
    def create(
        header: SeriesData,
        data: pd.DataFrame,
    ) -> PlateData:
        well_plate_id = header[str, "Barcode1"].strip("<>")
        well_data = [
            WellData.create(
                luminescence=value,
                location_id=f"{row_name}{col_name}_{row_index + 1}",
                well_plate_id=well_plate_id,
            )
            # Get each unique row label, and then iterate over all rows with that label.
            for row_name in data.index.unique()
            for row_index, (_, row) in enumerate(data.loc[[row_name]].iterrows())
            for col_name, value in row.items()
        ]
        return PlateData(
            measurement_time=header[str, "Read Time"],
            analyst=header.get(str, "User"),
            well_plate_id=well_plate_id,
            # The well count is (# of unique row labels) * (# of columns)
            plate_well_count=len(data.index.unique()) * data.shape[1],
            well_data=well_data,
        )


@dataclass(frozen=True)
class WellData:
    luminescence: int
    location_identifier: str
    sample_identifier: str

    @staticmethod
    def create(luminescence: int, location_id: str, well_plate_id: str) -> WellData:
        sample_id = well_plate_id + "_" + location_id
        return WellData(
            luminescence=luminescence,
            location_identifier=location_id,
            sample_identifier=sample_id,
        )


def create_metadata(header: Header, file_name: str) -> Metadata:
    asm_file_identifier = Path(file_name).with_suffix(".json")
    return Metadata(
        file_name=header.file_name.rsplit("\\", 1)[-1],
        unc_path=header.file_name,
        software_name=header.version,
        software_version=header.version,
        device_identifier=NOT_APPLICABLE,
        model_number=header.model,
        equipment_serial_number=header.serial_number,
        asm_file_identifier=asm_file_identifier.name,
        data_system_instance_id=NOT_APPLICABLE,
    )


def create_measurement_groups(plates: list[PlateData]) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(
            analyst=plate.analyst,
            measurement_time=plate.measurement_time,
            plate_well_count=plate.plate_well_count,
            measurements=[
                Measurement(
                    type_=MeasurementType.LUMINESCENCE,
                    identifier=random_uuid_str(),
                    luminescence=well.luminescence,
                    sample_identifier=well.sample_identifier,
                    location_identifier=well.location_identifier,
                    well_plate_identifier=plate.well_plate_id,
                    device_type=constants.LUMINESCENCE_DETECTOR,
                    detection_type=constants.LUMINESCENCE,
                )
            ],
        )
        for plate in plates
        for well in plate.well_data
    ]
