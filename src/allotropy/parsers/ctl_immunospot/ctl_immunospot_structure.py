from __future__ import annotations

from pathlib import PureWindowsPath
import re

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    ImageFeature,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.ctl_immunospot import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
)


def create_measurement_groups(
    plate_data: dict[str, pd.DataFrame],
    plate_identifier: str | None,
    header: SeriesData,
) -> list[MeasurementGroup]:
    well_plate_identifier = (
        plate_identifier or PureWindowsPath(header[str, "File path"]).stem
    )
    first_plate: pd.DataFrame = next(iter(plate_data.values()))
    # TODO: get well size
    plate_well_count = first_plate.size
    return [
        MeasurementGroup(
            plate_well_count=plate_well_count,
            measurement_time=header[str, ("Counted", "Review Date")],
            analyst=header[str, "Authenticated user"],
            measurements=[
                Measurement(
                    type_=MeasurementType.OPTICAL_IMAGING,
                    device_type=constants.DEVICE_TYPE,
                    identifier=random_uuid_str(),
                    well_plate_identifier=well_plate_identifier,
                    location_identifier=f"{row}{col}",
                    sample_identifier=f"{well_plate_identifier}_{row}{col}",
                    detection_type=constants.DETECTION_TYPE,
                    processed_data=ProcessedData(
                        identifier=random_uuid_str(),
                        features=[
                            ImageFeature(
                                identifier=random_uuid_str(),
                                feature=name,
                                result=float(data[col][row]),
                            )
                            for name, data in plate_data.items()
                        ],
                    ),
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
