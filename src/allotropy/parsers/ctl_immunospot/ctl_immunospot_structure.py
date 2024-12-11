from __future__ import annotations

from pathlib import PureWindowsPath
import re

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    ImageFeature,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.parsers.constants import NOT_APPLICABLE, round_to_nearest_well_count
from allotropy.parsers.ctl_immunospot import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
)


def _create_measurement(
    well_row: str,
    well_col: str,
    well_plate_identifier: str,
    plate_data: dict[str, pd.DataFrame],
    histograms: dict[str, tuple[list[float], list[float]]],
) -> Measurement:
    location_identifier = f"{well_row}{well_col}"
    return Measurement(
        type_=MeasurementType.OPTICAL_IMAGING,
        device_type=constants.DEVICE_TYPE,
        identifier=random_uuid_str(),
        well_plate_identifier=well_plate_identifier,
        location_identifier=location_identifier,
        sample_identifier=f"{well_plate_identifier}_{location_identifier}",
        detection_type=constants.DETECTION_TYPE,
        processed_data=ProcessedData(
            identifier=random_uuid_str(),
            features=[
                ImageFeature(
                    identifier=random_uuid_str(),
                    feature=name,
                    result=float(data[well_col][well_row]),
                )
                for name, data in plate_data.items()
            ],
        ),
        custom_data_cubes=[
            DataCube(
                label="spot count histogram",
                structure_dimensions=[
                    DataCubeComponent(
                        concept="spot size",
                        type_=FieldComponentDatatype.double,
                        unit=UNITLESS,
                    )
                ],
                structure_measures=[
                    DataCubeComponent(
                        concept="spot count",
                        type_=FieldComponentDatatype.double,
                        unit="Number",
                    )
                ],
                dimensions=[histograms[location_identifier][0]],
                measures=[histograms[location_identifier][1]],
            )
        ]
        if histograms and location_identifier in histograms
        else None,
    )


def create_measurement_groups(
    header: SeriesData,
    plate_identifier: str | None,
    plate_data: dict[str, pd.DataFrame],
    histograms: dict[str, tuple[list[float], list[float]]],
) -> list[MeasurementGroup]:
    well_plate_identifier = (
        plate_identifier or PureWindowsPath(header[str, "File path"]).stem
    )
    first_plate: pd.DataFrame = next(iter(plate_data.values()))
    plate_well_count = assert_not_none(
        round_to_nearest_well_count(first_plate.size),
        f"Unable to determine valid plate count from dataframe of size: {first_plate.size}",
    )
    return [
        MeasurementGroup(
            plate_well_count=plate_well_count,
            measurement_time=header[str, ("Counted", "Review Date")],
            analyst=header[str, "Authenticated user"],
            measurements=[
                _create_measurement(
                    row, col, well_plate_identifier, plate_data, histograms
                )
            ],
        )
        for row in first_plate.index
        for col in first_plate.columns
    ]


def create_metadata(header: SeriesData) -> Metadata:
    path = PureWindowsPath(header[str, "File path"])
    return Metadata(
        file_name=path.name,
        unc_path=str(path),
        device_identifier=NOT_APPLICABLE,
        model_number=assert_not_none(
            re.match(r"^(\w+)-(\w+)", header[str, "Analyzer Serial number"]),
            msg="Unable to parse analyzer serial number.",
        ).group(1),
        data_system_instance_id=header[str, "Computer name"],
        equipment_serial_number=header[str, "Analyzer Serial number"],
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        software_name=constants.SOFTWARE_NAME,
        software_version=assert_not_none(
            re.match(r"^ImmunoSpot ([\d\.]+)$", header[str, "Software version"]),
            msg="Unable to parse software version",
        ).group(1),
    )
