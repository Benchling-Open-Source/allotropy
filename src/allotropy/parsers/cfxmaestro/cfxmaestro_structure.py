from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import pandas as pd

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
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


def create_metadata(file_path: str) -> Metadata:
    return Metadata(
        device_type=constants.DEVICE_TYPE,
        device_serial_number=NOT_APPLICABLE,
        file_name=Path(file_path).name,
        unc_path=file_path,
        experiment_type=ExperimentType.comparative_CT_qPCR_experiment,
        container_type=constants.CONTAINER_TYPE,
        software_name=constants.SOFTWARE_NAME,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_identifier=NOT_APPLICABLE,
        model_number=NOT_APPLICABLE,
        measurement_method_identifier=NOT_APPLICABLE,
    )


def create_measurement_group(
    well_data: list[SeriesData],
    plate_well_count: int,
) -> MeasurementGroup:
    return MeasurementGroup(
        plate_well_count=plate_well_count,
        measurements=[
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
                sample_role_type=data.get(str, "Content"),
                well_location_identifier=data[str, "Well"],
                # Optional settings
                reporter_dye_setting=data[str, "Fluor"],
                # Processed data
                processed_data=ProcessedData(
                    # TODO: add add error document (or omit?) if Cq is NaN.
                    cycle_threshold_result=data.get(
                        float, "Cq", validate=SeriesData.NOT_NAN
                    ),
                    # TODO: confirm the exported column name for cycle number
                    cycle_threshold_value_setting=data.get(
                        float, "Cycle Number", NEGATIVE_ZERO
                    ),
                ),
            )
            for data in well_data
            if data.get(str, "Sample", validate=SeriesData.NOT_NAN)
            or data.get(float, "Cq", validate=SeriesData.NOT_NAN)
        ],
    )


def create_measurement_groups(df: pd.DataFrame) -> list[MeasurementGroup]:
    well_to_rows = defaultdict(list)

    def map_to_dict(data: SeriesData) -> None:
        well_to_rows[data[str, "Well"]].append(deepcopy(data))

    map_rows(df, map_to_dict)

    groups = [
        create_measurement_group(well_to_rows[well_id], len(well_to_rows))
        for well_id in well_to_rows
    ]
    return [group for group in groups if group.measurements]
