from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.pcr.rec._2024._09.qpcr import (
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
)
from allotropy.parsers.cfxmaestro import constants
from allotropy.parsers.constants import (
    DEFAULT_EPOCH_TIMESTAMP,
    NEGATIVE_ZERO,
    NOT_APPLICABLE,
)
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_nan


def create_metadata(file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        asm_file_identifier=path.with_suffix(".json").name,
        unc_path=file_path,
        experiment_type=constants.EXPERIMENT_TYPE,
        container_type=constants.CONTAINER_TYPE,
        software_name=constants.SOFTWARE_NAME,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_type=constants.DEVICE_TYPE,
        device_serial_number=NOT_APPLICABLE,
        device_identifier=NOT_APPLICABLE,
        data_system_instance_identifier=NOT_APPLICABLE,
        model_number=NOT_APPLICABLE,
        measurement_method_identifier=NOT_APPLICABLE,
    )


def create_measurement_group(
    well_data: list[SeriesData],
    plate_well_count: int,
) -> MeasurementGroup:
    measurements = []
    for data in well_data:
        if not (
            data.get(str, "Sample", validate=SeriesData.NOT_NAN)
            or data.get(float, "Cq", validate=SeriesData.NOT_NAN)
        ):
            data.get_unread()
            continue
        sample_doc_custom_data = data.get_custom_keys(
            set(constants.SAMPLE_DOCUMENT_CUSTOM_KEYS)
        )
        device_doc_custom_data = data.get_custom_keys(
            set(constants.DEVICE_CONTROL_DOCUMENT_CUSTOM_KEYS)
        )
        processed_data_doc_custom_data = data.get_custom_keys(
            set(constants.PROCESSED_DATA_DOCUMENT_CUSTOM_KEYS)
        )
        # these fields are not need in the asm
        data.mark_read(
            {
                "Cq Mean",
                "Unnamed: 0",
            }
        )
        measurements.append(
            Measurement(
                # Measurement metadata
                identifier=random_uuid_str(),
                sample_identifier=data.get(
                    str, "Sample", NOT_APPLICABLE, SeriesData.NOT_NAN
                ),
                target_identifier=data.get(
                    str, "Target", NOT_APPLICABLE, SeriesData.NOT_NAN
                ),
                group_identifier=data.get(
                    str, "Biological Set Name", NOT_APPLICABLE, SeriesData.NOT_NAN
                ),
                timestamp=DEFAULT_EPOCH_TIMESTAMP,
                # Optional measurement metadata
                sample_role_type=constants.SAMPLE_ROLE_TYPES_MAP.get(
                    data.get(str, "Content", "__INVALID_KEY__")
                ),
                location_identifier=data[str, "Well"],
                well_location_identifier=data[str, "Well"],
                # Optional settings
                reporter_dye_setting=data[str, "Fluor"],
                # Processed data
                processed_data=ProcessedData(
                    # TODO: add add error document (or omit?) if Cq is NaN.
                    cycle_threshold_result=data.get(
                        float, "Cq", validate=SeriesData.NOT_NAN
                    ),
                    # TODO: cycle number is required, but we do not have any examples of the value being
                    # provided, if we get one, and the column does not match, update here.
                    cycle_threshold_value_setting=(
                        cycle_number := data.get(float, "Cycle Number", NEGATIVE_ZERO)
                    ),
                    custom_info=_set_nan_to_string(processed_data_doc_custom_data),
                ),
                # Since the processed data doc does not include an error document,
                # we added the cycle threshold value setting error at measurement level
                error_document=(
                    [
                        Error(
                            error="Value not provided in instrument file",
                            feature="cycle threshold value setting (qPCR)",
                        )
                    ]
                    if cycle_number == NEGATIVE_ZERO
                    else None
                ),
                sample_custom_info=_set_nan_to_string(sample_doc_custom_data),
                device_control_custom_info=_set_nan_to_string(device_doc_custom_data),
                custom_info=data.get_unread(),
            )
        )

    return MeasurementGroup(
        plate_well_count=plate_well_count,
        well_volume=NEGATIVE_ZERO,
        error_document=[
            Error(error="Value not provided in instrument file", feature="well volume")
        ],
        experimental_data_identifier=NOT_APPLICABLE,
        measurements=measurements,
    )


def create_measurement_groups(df: pd.DataFrame) -> list[MeasurementGroup]:
    well_to_rows = defaultdict(list)

    def map_to_dict(data: SeriesData) -> None:
        well_to_rows[data[str, "Well"]].append(deepcopy(data))
        data.get_unread()

    map_rows(df, map_to_dict)

    groups = [
        create_measurement_group(well_to_rows[well_id], len(well_to_rows))
        for well_id in well_to_rows
    ]
    return [group for group in groups if group.measurements]


def _set_nan_to_string(data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: try_float_or_nan(value) if isinstance(value, float) else value
        for key, value in data.items()
    }
