from __future__ import annotations

import re

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    ImageFeature,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.mabtech_apex.mabtech_apex_contents import MabtechApexContents
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_from_series_or_nan,
    try_float_from_series_or_none,
    try_str_from_series,
    try_str_from_series_or_none,
)

IMAGE_FEATURES = [
    "Spot Forming Units (SFU)",
    "Average Relative Spot Volume (RSV)",
    "Sum of Spot Volume (RSV)",
]


def _create_metadata(contents: MabtechApexContents, file_name: str) -> Metadata:
    machine_id = assert_not_none(
        re.match(
            "([A-Z]+[a-z]+) ([0-9]+)",
            try_str_from_series(contents.plate_info, key="Machine ID:"),
        ),
        msg="Unable to interpret Machine ID",
    )

    return Metadata(
        device_identifier=NOT_APPLICABLE,
        device_type="imager",
        detection_type="optical-imaging",
        software_name="Apex",
        unc_path=try_str_from_series_or_none(contents.plate_info, key="Path:"),
        software_version=try_str_from_series_or_none(
            contents.plate_info, key="Software Version:"
        ),
        model_number=machine_id.group(1),
        equipment_serial_number=machine_id.group(2),
        file_name=file_name,
        analyst=try_str_from_series_or_none(contents.plate_info, key="Saved By:"),
    )


def _create_measurement(plate_data: pd.Series[str]) -> Measurement:
    location_id = try_str_from_series(plate_data, "Well")
    well_plate = try_str_from_series_or_none(plate_data, "Plate")

    return Measurement(
        type_=MeasurementType.OPTICAL_IMAGING,
        identifier=random_uuid_str(),
        measurement_time=try_str_from_series(plate_data, "Read Date"),
        location_identifier=location_id,
        well_plate_identifier=well_plate,
        sample_identifier=f"{well_plate}_{location_id}",
        exposure_duration_setting=try_float_from_series_or_none(plate_data, "Exposure"),
        illumination_setting=try_float_from_series_or_none(
            plate_data, "Preset Intensity"
        ),
        processed_data=ProcessedData(
            identifier=random_uuid_str(),
            features=[
                ImageFeature(
                    identifier=random_uuid_str(),
                    feature=feature,
                    result=try_float_from_series_or_nan(plate_data, feature),
                )
                for feature in IMAGE_FEATURES
            ],
        ),
    )


def _create_groups(contents: MabtechApexContents) -> list[MeasurementGroup]:
    # if Read Date is not present in file, return None, no measurement for given Well
    plate_data = contents.data.dropna(subset="Read Date")

    return list(
        plate_data.apply(  # type: ignore[call-overload]
            lambda data: MeasurementGroup(
                measurements=[_create_measurement(data)],
                plate_well_count=96,
            ),
            axis="columns",
        )
    )


def create_data(contents: MabtechApexContents, file_name: str) -> Data:
    return Data(_create_metadata(contents, file_name), _create_groups(contents))
