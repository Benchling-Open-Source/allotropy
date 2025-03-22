from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.constants import (
    DEFAULT_EPOCH_TIMESTAMP,
    get_well_count_by_well_ids,
    NOT_APPLICABLE,
)
from allotropy.parsers.msd_workbench.constants import (
    DETECTION_TYPE,
    DEVICE_TYPE,
    SAMPLE_ROLE_TYPE_MAPPING,
    SOFTWARE_NAME,
)
from allotropy.parsers.msd_workbench.msd_workbench_calculated_data_mapping import (
    CalculatedDataColumns,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass(frozen=True)
class PlateData:
    measurement_time: str
    plate_well_count: int
    well_plate_id: str
    well_data: pd.DataFrame

    @staticmethod
    def create(
        data: pd.DataFrame,
        well_plate_id: str,
    ) -> PlateData:
        plate_well_count = PlateData._get_plate_well_count(data)
        if not plate_well_count:
            msg = "Could not determine plate well count"
            raise AllotropyParserError(msg)

        return PlateData(
            measurement_time=DEFAULT_EPOCH_TIMESTAMP,
            well_plate_id=well_plate_id,
            plate_well_count=plate_well_count,
            well_data=data,
        )

    @staticmethod
    def _get_plate_well_count(data: pd.DataFrame) -> int | None:
        return get_well_count_by_well_ids(
            well_identifiers=[int(well[-1]) for well in data["Well"]],
            well_locations=data["Well"].astype(str).tolist(),
        )


def create_metadata(file_name: str) -> Metadata:
    asm_file_identifier = Path(file_name).with_suffix(".json")
    return Metadata(
        file_name=file_name.rsplit("\\", 1)[-1],
        unc_path=file_name,
        software_name=SOFTWARE_NAME,
        device_identifier=NOT_APPLICABLE,
        model_number=NOT_APPLICABLE,
        asm_file_identifier=asm_file_identifier.name,
        data_system_instance_id=NOT_APPLICABLE,
    )


def create_measurement_groups(plate_data: PlateData) -> list[MeasurementGroup]:
    def map_measurement(row: SeriesData) -> Measurement:
        sample_id = f"{row[str, 'Sample']}_{row[str, 'Well']}"
        custom_info = {
            "detection range": row.get(str, "Detection Range"),
            "assay identifier": row.get(str, "Assay"),
        }
        return Measurement(
            type_=MeasurementType.LUMINESCENCE,
            identifier=random_uuid_str(),
            luminescence=row[float, "Signal"],
            sample_identifier=sample_id,
            location_identifier=row[str, "Spot"],
            well_location_identifier=row[str, "Well"],
            well_plate_identifier=plate_data.well_plate_id,
            device_type=DEVICE_TYPE,
            detection_type=DETECTION_TYPE,
            mass_concentration=row.get(float, "Concentration"),
            sample_role_type=SAMPLE_ROLE_TYPE_MAPPING.get(
                row[str, "Sample"][0].lower()
            ),
            sample_custom_info={
                "dilution factor setting": row.get(int, "Dilution Factor"),
            },
            measurement_custom_info={
                **custom_info,
                **_filter_calculated_data_fields(row.get_unread()),
            },
        )

    measurements = map_rows(plate_data.well_data, map_measurement)

    grouped_measurements = defaultdict(list)
    for measurement in measurements:
        grouped_measurements[measurement.sample_identifier].append(measurement)

    return [
        MeasurementGroup(
            measurement_time=plate_data.measurement_time,
            plate_well_count=plate_data.plate_well_count,
            measurements=group,
        )
        for group in grouped_measurements.values()
    ]


def _filter_calculated_data_fields(unread_data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in unread_data.items()
        if key not in {col.value for col in CalculatedDataColumns}
    }
