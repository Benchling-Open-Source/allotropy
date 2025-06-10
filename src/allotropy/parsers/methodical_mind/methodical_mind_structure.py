from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

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


def _is_valid_well_label(label: str) -> bool:
    return bool(re.match("[A-Z]+", label))


@dataclass(frozen=True)
class PlateData:
    measurement_time: str
    plate_well_count: int
    analyst: str | None
    well_plate_id: str
    well_data: list[WellData]
    measurement_custom_info: dict[str, Any]
    sample_custom_info: dict[str, Any]
    device_custom_info: dict[str, Any]

    @staticmethod
    def create(
        header: SeriesData,
        data: pd.DataFrame,
    ) -> PlateData:
        well_plate_id = header[str, "Barcode1"].strip("<>")
        unique_well_labels = [
            label for label in data.index.unique() if _is_valid_well_label(label)
        ]
        spot_id = header.get(int, "SpotID")
        well_data = [
            WellData.create(
                luminescence=float(value),
                location_id=str(spot_id or row_index + 1),
                well_plate_id=well_plate_id,
                well_location_id=f"{row_name}{col_name}",
            )
            # Get each unique row label, and then iterate over all rows with that label.
            for row_name in unique_well_labels
            for row_index, (_, row) in enumerate(data.loc[[row_name]].iterrows())
            for col_name, value in row.items()
            if _is_valid_well_label(row_name)
            # Only include if the measurement is not an empty string, this skips blank entries for non-visible
            # measurements.
            if str(value).strip()
        ]
        return PlateData(
            measurement_time=header[str, "Read Time"],
            analyst=header.get(str, "User"),
            well_plate_id=well_plate_id,
            # The well count is (# of unique row labels) * (# of columns)
            plate_well_count=len(unique_well_labels) * data.shape[1],
            well_data=well_data,
            sample_custom_info=header.get_custom_keys(
                {"Barcode2", "Barcode3", "Plate #", "Stack ID"}
            ),
            device_custom_info=header.get_custom_keys(
                {"Orient", "Spots Per Well", "Det Param"}
            ),
            measurement_custom_info=header.get_unread(
                # fields already mapped
                skip={
                    "Type",
                    "Wells Per Col",
                    "Wells Per Row",
                }
            ),
        )


@dataclass(frozen=True)
class WellData:
    luminescence: float
    location_identifier: str
    sample_identifier: str
    well_location_identifier: str

    @staticmethod
    def create(
        luminescence: float, location_id: str, well_plate_id: str, well_location_id: str
    ) -> WellData:
        sample_id = well_plate_id + "_" + well_location_id
        return WellData(
            luminescence=luminescence,
            location_identifier=location_id,
            sample_identifier=sample_id,
            well_location_identifier=well_location_id,
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
    plates_data = []
    plates_by_id: defaultdict[str, list[PlateData]] = defaultdict(list)
    for plate in plates:
        plates_by_id[plate.well_plate_id].append(plate)

    for plates in plates_by_id.values():
        grouped_wells: defaultdict[str, list[WellData]] = defaultdict(list)
        for plate in plates:
            for well in plate.well_data:
                grouped_wells[well.well_location_identifier].append(well)
        plates_data.extend(
            [
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
                            well_location_identifier=well.well_location_identifier,
                            well_plate_identifier=plate.well_plate_id,
                            device_type=constants.LUMINESCENCE_DETECTOR,
                            detection_type=constants.LUMINESCENCE,
                            measurement_custom_info=plate.measurement_custom_info,
                            sample_custom_info=plate.sample_custom_info,
                            device_control_custom_info=plate.device_custom_info,
                        )
                        for well in well_group
                    ],
                )
                for well_group in grouped_wells.values()
            ]
        )

    return plates_data
