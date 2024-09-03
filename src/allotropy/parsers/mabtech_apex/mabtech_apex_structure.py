from __future__ import annotations

import re

from allotropy.allotrope.models.shared.definitions.definitions import NaN
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    ImageFeature,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
)
from allotropy.exceptions import AllotropeParsingError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.mabtech_apex import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none


def create_metadata(plate_info: SeriesData, file_name: str) -> Metadata:
    machine_id = assert_not_none(
        re.match(
            "([A-Z]+[a-z]*) ([0-9]+)",
            plate_info[str, "Machine ID:"],
        ),
        msg="Unable to interpret Machine ID",
    )

    return Metadata(
        device_identifier=NOT_APPLICABLE,
        software_name=constants.SOFTWARE_NAME,
        unc_path=plate_info.get(str, "Path:"),
        software_version=plate_info.get(str, "Software Version:"),
        model_number=machine_id.group(1),
        equipment_serial_number=machine_id.group(2),
        file_name=file_name,
    )


def _create_measurement(plate_data: SeriesData) -> Measurement:
    location_id = plate_data[str, "Well"]
    well_plate = plate_data.get(str, "Plate")
    led_filter = plate_data.get(str, "LED Filter")
    led_filter_without_total = led_filter.split(" ")[0] if led_filter else None
    exposure_duration_setting_key = (
        f"{led_filter_without_total} Exposure"
        if led_filter_without_total
        else "Exposure"
    )
    illumination_setting_key = (
        f"{led_filter_without_total} Preset Intensity"
        if led_filter_without_total
        else "Preset Intensity"
    )
    return Measurement(
        type_=MeasurementType.OPTICAL_IMAGING,
        identifier=random_uuid_str(),
        location_identifier=location_id,
        well_plate_identifier=well_plate,
        sample_identifier=f"{well_plate}_{location_id}",
        detection_type=constants.DETECTION_TYPE,
        device_type=constants.DEVICE_TYPE,
        led_filter=led_filter,
        exposure_duration_setting=plate_data.get(float, exposure_duration_setting_key),
        illumination_setting=plate_data.get(float, illumination_setting_key),
        processed_data=ProcessedData(
            identifier=random_uuid_str(),
            features=[
                ImageFeature(
                    identifier=random_uuid_str(),
                    feature=_format_feature_name(feature, led_filter),
                    result=plate_data.get(float, feature, NaN),
                )
                for feature in constants.IMAGE_FEATURES
                if plate_data.get(float, feature)
            ],
        ),
    )


def _format_feature_name(feature: str, led_filter: str | None) -> str:
    if led_filter:
        led_number = re.search(r"\d+", led_filter)
        if not led_number:
            error_msg = f"Unable to interpret LED number from {led_filter}"
            raise AllotropeParsingError(error_msg)
        feature = feature.format(filter=led_filter, led_number=led_number.group())
    else:
        feature = feature.format(filter="", led_number="").replace("  ", " ")
    return feature


def create_measurement_group(
    data: SeriesData, plate_info: SeriesData
) -> MeasurementGroup:
    return MeasurementGroup(
        measurements=[_create_measurement(data)],
        plate_well_count=96,
        measurement_time=data[str, "Read Date"],
        analyst=plate_info.get(str, "Saved By:"),
    )
