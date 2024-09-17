from __future__ import annotations

import logging
import re

from allotropy.allotrope.models.shared.definitions.units import UNITLESS
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
    filters = led_filter_without_total.split("+") if led_filter_without_total else []
    exposure_duration_setting_key = (
        f"{led_filter_without_total} Exposure"
        if led_filter_without_total and len(filters) == 1
        else "Exposure"
    )
    illumination_setting_key = (
        f"{led_filter_without_total} Preset Intensity"
        if led_filter_without_total and len(filters) == 1
        else "Preset Intensity"
    )

    feature_names = _build_feature_names(filters)
    features = [
        feature
        for feature_name in feature_names
        if (feature := _build_feature(feature_name, plate_data))
    ]

    measurement = Measurement(
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
        illumination_setting_unit=UNITLESS,
        processed_data=ProcessedData(
            identifier=random_uuid_str(),
            features=features,
        ),
    )
    if not (measurement.processed_data and measurement.processed_data.features):
        logging.warning(f"no image features identified for {well_plate}")
    return measurement


def _build_feature_names(led_filters: list[str]) -> list[str]:
    feature_names = []
    seen = set()

    for feature in constants.IMAGE_FEATURES:
        if not led_filters:
            formatted_feature = feature.format(filter="", led_number="")
            if formatted_feature not in seen:
                feature_names.append(formatted_feature)
                seen.add(formatted_feature)
            continue
        for led_filter in led_filters:
            led_number = re.search(r"\d+", led_filter)
            if not led_number:
                error_msg = f"Unable to interpret LED number from {led_filter}"
                raise AllotropeParsingError(error_msg)

            formatted_feature = feature.format(
                filter=led_filter, led_number=led_number.group()
            )
            if formatted_feature not in seen:
                feature_names.append(formatted_feature)
                seen.add(formatted_feature)

    return feature_names


def _build_feature(feature: str, plate_data: SeriesData) -> ImageFeature | None:
    value = plate_data.get(float, feature)
    if value is None:
        return None
    return ImageFeature(identifier=random_uuid_str(), feature=feature, result=value)


def create_measurement_group(
    well_data: list[SeriesData], plate_info: SeriesData
) -> MeasurementGroup:
    measurements = [_create_measurement(well_row) for well_row in well_data]
    return MeasurementGroup(
        measurements=measurements,
        plate_well_count=96,
        measurement_time=well_data[0][str, "Read Date"],
        analyst=plate_info.get(str, "Saved By:"),
    )
