from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Measurement,
    MeasurementGroup,
    Metadata,
    CalculatedDataDocumentItem,
    CalculatedDataItem,
    ProcessedDataDocumentItem,
    ProcessedDataAggregateDocument,
    DataSource,

)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.parsers.cfxmaestro import constants
from allotropy.parsers.utils.pandas import SeriesData, map_rows
from allotropy.parsers.utils.uuids import random_uuid_str
from dataclasses import dataclass
import pandas as pd



def create_metadata(data: SeriesData, file_name: str) -> Metadata:
    return Metadata(

        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        file_name=file_name,
        software_name=constants.SOFTWARE_NAME,
        container_type=constants.CONTAINER_TYPE,
        device_type=constants.DEVICE_TYPE,


        #TypeError: Metadata.__init__() missing 7 required positional arguments: 'device_identifier', 'device_serial_number', 'model_number', 'data_system_instance_identifier', 'unc_path', 'experiment_type', and 'measurement_method_identifier'

         #adding in feilds from Termainal (above) about requred feilds, set them to N/A using constants tab

        device_identifier=constants.NOT_APPLICABLE,
        device_serial_number=constants.NOT_APPLICABLE,
        model_number=constants.NOT_APPLICABLE,
        data_system_instance_identifier=constants.NOT_APPLICABLE,
        unc_path=constants.NOT_APPLICABLE,
        experiment_type=constants.NOT_APPLICABLE,
        measurement_method_identifier=constants.NOT_APPLICABLE,

    )

#read well, count

def create_measurement_group(data: SeriesData) -> MeasurementGroup:
    # This function will be called for every row in the dataset, use it to create
    # a corresponding measurement group.

    return MeasurementGroup(
        plate_well_count=constants.PLATE_WELL_COUNT,


        analyst=constants.NOT_APPLICABLE,
        experimental_data_identifier=constants.NOT_APPLICABLE,
        measurements=[
            Measurement(

                #Measurement Meta Data
                identifier=random_uuid_str(),


                #Is this a good way to generate a timestamp for this .CSV file
                #Use EPOCH in COnstants tab


                sample_identifier=data[str, "Sample"],
                target_idenitifier=constants.NOT_APPLICABLE,
                group_identifier=data[str,"Biological Set Name"],

                #Settings
                pcr_detection_chemistry=constants.NOT_APPLICABLE,

                #Optional Measurement Metadata
                sample_role_type=data[str,"Content"],
                well_location_identifier=data[str,"Well"],

                #Optional Settings
                reporter_dye_setting=data[str,"Flour"],

                #Processed Data
                processed_data=data[float,"Cq"],

            )
        ],
    )

def create_measurement_groups(df: pd.DataFrame) -> list[MeasurementGroup]:
    print(df.shape)
    assert False
    return map_rows(df, create_measurement_groups)
