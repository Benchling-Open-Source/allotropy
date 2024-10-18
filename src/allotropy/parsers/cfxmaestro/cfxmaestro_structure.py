from collections import defaultdict

import pandas as pd  # type: ignore

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
)
from allotropy.parsers.cfxmaestro import constants
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(file_name: str) -> Metadata:
    return Metadata(
        device_type=constants.DEVICE_TYPE,
        device_serial_number=constants.NOT_APPLICABLE,
        file_name=file_name,
        experiment_type=ExperimentType.comparative_CT_qPCR_experiment,
        container_type=constants.CONTAINER_TYPE,
        software_name=constants.SOFTWARE_NAME,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_identifier=constants.NOT_APPLICABLE,
        model_number=constants.NOT_APPLICABLE,
        measurement_method_identifier=constants.NOT_APPLICABLE,
        unc_path=constants.NOT_APPLICABLE,
    )

#well_to_rows = defaultdict(list)

#def map_to_dict(data: SeriesData) -> None:
#        well_to_rows[data[str, "Well"]].append(data)
#
#        map_rows(df, map_to_dict)

def create_measurement_group(
    well_data: list[SeriesData], plate_well_count: int,
) -> MeasurementGroup:
    return MeasurementGroup(
        plate_well_count= plate_well_count,
        analyst=constants.NOT_APPLICABLE,
        measurements=[
            Measurement(
                # Measurement Meta Data
                identifier=random_uuid_str(),
                # Is this a good way to generate a timestamp for this .CSV file
                timestamp=constants.DEFAULT_EPOCH_TIMESTAMP,
                sample_identifier=data.get(str, "Sample"),
                target_identifier=constants.NOT_APPLICABLE,
                group_identifier=data.get(str, "Biological Set Name"),
                # Optional Measurement Metadata
                sample_role_type=data.get(str, "Content"),
                well_location_identifier=data[str, "Well"],
                # Optional Settings
                reporter_dye_setting=data[str, "Fluor"],
                # Processed Data
                processed_data=ProcessedData(
                    cycle_threshold_result=data[float, "Cq"],
                    # TODO: get the exported column name for cycle number
                    cycle_threshold_value_setting=data.get(float, "Cycle Number", -0),
                ),
            )
            for data in well_data
        ],
    )
