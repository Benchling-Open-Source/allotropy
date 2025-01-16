from __future__ import annotations

from pathlib import Path

from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.dpcr import (
    Measurement,
    Metadata,
)
from allotropy.exceptions import get_key_or_error
from allotropy.parsers.constants import DEFAULT_EPOCH_TIMESTAMP
from allotropy.parsers.qiacuity_dpcr.constants import (
    BRAND_NAME,
    DEVICE_IDENTIFIER,
    DEVICE_TYPE,
    PRODUCT_MANUFACTURER,
    SAMPLE_ROLE_TYPE_MAPPING,
    SOFTWARE_NAME,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_measurements(data: SeriesData) -> Measurement:
    sample_role_type = data.get(str, "Type")
    # TODO: When the sample role type model is updated in this repo, we should update this
    # Map sample role types to valid sample role types from ASM
    if sample_role_type is not None:
        sample_role_type = get_key_or_error(
            "sample type", sample_role_type, SAMPLE_ROLE_TYPE_MAPPING
        )

    return Measurement(
        identifier=random_uuid_str(),
        measurement_time=DEFAULT_EPOCH_TIMESTAMP,
        sample_identifier=data[str, "Sample/NTC/Control"],
        sample_role_type=sample_role_type,
        location_identifier=data[str, "Well Name"],
        plate_identifier=data.get(str, "Plate ID"),
        target_identifier=data[str, "Target"],
        total_partition_count=data[int, "Partitions (valid)"],
        concentration=data[float, ["Concentration (copies/μL)", "Conc. [copies/μL]"]],
        positive_partition_count=data[int, "Partitions (positive)"],
        negative_partition_count=data.get(int, "Partitions (negative)"),
        fluorescence_intensity_threshold_setting=data.get(float, "Threshold"),
    )


def create_metadata(file_path: str) -> Metadata:
    return Metadata(
        device_identifier=DEVICE_IDENTIFIER,
        brand_name=BRAND_NAME,
        device_type=DEVICE_TYPE,
        software_name=SOFTWARE_NAME,
        product_manufacturer=PRODUCT_MANUFACTURER,
        file_name=Path(file_path).name,
        unc_path=file_path,
    )
