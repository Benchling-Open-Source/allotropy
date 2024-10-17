from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    CalculatedDataDocumentItem,
    CalculatedDataItem,
    DataSource,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
)
from allotropy.parsers.cfxmaestro import constants
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(data: SeriesData, file_name: str) -> Metadata:
    return Metadata(
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        file_name=file_name,
        software_name=constants.SOFTWARE_NAME,
        container_type=constants.CONTAINER_TYPE,
        device_type=constants.DEVICE_TYPE,
        device_identifier=constants.NOT_APPLICABLE,
        device_serial_number=constants.NOT_APPLICABLE,
        model_number=constants.NOT_APPLICABLE,
        experiment_type=ExperimentType.comparative_CT_qPCR_experiment,

        #TypeError: Metadata.__init__() missing 7 required positional arguments: 'device_identifier', 'device_serial_number', 'model_number', 'data_system_instance_identifier', 'unc_path', 'experiment_type', and 'measurement_method_identifier'

         #adding in feilds from Termainal (above) about requred feilds, set them to N/A using constants tab

        unc_path=constants.NOT_APPLICABLE,
        measurement_method_identifier=constants.NOT_APPLICABLE,
    )

#read well, count

def create_measurement_group(well_data: list[SeriesData], plate_well_count: int) -> MeasurementGroup:
    # This function will be called for every row in the dataset, use it to create
    # a corresponding measurement group.
    return MeasurementGroup(
        plate_well_count=plate_well_count,
        analyst=constants.NOT_APPLICABLE,
        experimental_data_identifier=constants.NOT_APPLICABLE,
        measurements=[
            Measurement(
                #Measurement Meta Data
                identifier=random_uuid_str(),
                #Is this a good way to generate a timestamp for this .CSV file
                timestamp=constants.DEFAULT_EPOCH_TIMESTAMP,

                sample_identifier=data[str, "Sample"],
                target_identifier=constants.NOT_APPLICABLE,
                group_identifier=data.get(str, "Biological Set Name"),

                #Settings
                
                #Optional Measurement Metadata
                sample_role_type=data[str, "Content"],
                well_location_identifier=data[str, "Well"],

                #Optional Settings
                reporter_dye_setting=data[str, "Fluor"],

                #Processed Data
                processed_data=ProcessedData(
                    cycle_threshold_result=data[float, "Cq"],
                    # TODO: get the exported column name for cycle number
                    cycle_threshold_value_setting=data.get(float, "Cycle Number", -0)
                )

            )
            for data in well_data
        ],
    )


def create_measurement_groups(df: pd.DataFrame) -> list[MeasurementGroup]:
    well_to_rows = defaultdict(list)

    def map_to_dict(data: SeriesData) -> None:
        well_to_rows[data[str, "Well"]].append(data)

    map_rows(df, map_to_dict)

    return [
        create_measurement_group(row_data, len(well_to_rows))
        for row_data in well_to_rows.values()
    ]
