from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.cfxmaestro import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str



def create_metadata(data: SeriesData, file_name: str) -> Metadata:
    return Metadata(

        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        file_name=file_name,
        software_name=constants.SOFTWARE_NAME,
        container_type=constants.CONTAINER_TYPE,
        device_type=constants.DEVICE_TYPE,

        #plate_well_count=constants.PLATE_WELL_COUNT,


    )


def create_measurement_groups(data: SeriesData) -> MeasurementGroup:
    # This function will be called for every row in the dataset, use it to create
    # a corresponding measurement group.
    return MeasurementGroup(
        plate_well_count=constants.PLATE_WELL_COUNT,
        #analyst=data[str, "Analyst"],

        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                identifier=random_uuid_str(),
            



                #timestamp=_format_timestamp(data[str, "NAME"]),

                #well_location_identifier=data[str,"Well"],
                sample_identifier=data[str, "Sample"],
                sample_role_type=data[str,"Content"],
                processed_data=data[float,"Cq"],



            )
        ],
    )
def _format_timestamp(timestamp: str) -> str:
    return timestamp.split("-")[0]
