from __future__ import annotations

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.qiacuity_dpcr.constants import (
    BRAND_NAME,
    DEVICE_IDENTIFIER,
    DEVICE_TYPE,
    EPOCH,
    PRODUCT_MANUFACTURER,
    SAMPLE_ROLE_TYPE_MAPPING,
    SOFTWARE_NAME,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def _create_measurements(data: SeriesData) -> Measurement:
    sample_role_type = data.get(str, "Type")
    # TODO: When the sample role type model is updated in this repo, we should update this
    # Map sample role types to valid sample role types from ASM
    if sample_role_type is not None:
        try:
            sample_role_type = SAMPLE_ROLE_TYPE_MAPPING[sample_role_type]
        except KeyError as e:
            error_message = (
                f"Unexpected sample typze found: {sample_role_type}. "
                f"Must be one of {list(SAMPLE_ROLE_TYPE_MAPPING.keys())}"
            )
            raise AllotropeConversionError(error_message) from e

    return Measurement(
        identifier=random_uuid_str(),
        measurement_time=EPOCH,
        sample_identifier=data[str, "Sample/NTC/Control"],
        sample_role_type=sample_role_type,
        location_identifier=data[str, "Well Name"],
        plate_identifier=data.get(str, "Plate ID"),
        target_identifier=data[str, "Target"],
        total_partition_count=data[int, "Partitions (valid)"],
        concentration=data[float, "Concentration (copies/µL)"],
        positive_partition_count=data[int, "Partitions (positive)"],
        negative_partition_count=data.get(int, "Partitions (negative)"),
        flourescence_intensity_threshold_setting=data.get(float, "Threshold"),
    )


def create_data(data: pd.DataFrame, file_name: str) -> Data:
    return Data(
        Metadata(
            device_identifier=DEVICE_IDENTIFIER,
            brand_name=BRAND_NAME,
            device_type=DEVICE_TYPE,
            software_name=SOFTWARE_NAME,
            product_manufacturer=PRODUCT_MANUFACTURER,
            file_name=file_name,
        ),
        measurement_groups=[
            MeasurementGroup(
                measurements=map_rows(data, _create_measurements),
                # TODO: Hardcoded plate well count to 0 since it's a required field
                #  ASM will be modified to optional in future version
                plate_well_count=0,
            )
        ],
    )
