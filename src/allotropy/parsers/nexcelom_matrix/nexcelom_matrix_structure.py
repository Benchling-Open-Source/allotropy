from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.nexcelom_matrix import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(file_name: str) -> Metadata:
    return Metadata(
        file_name=file_name,
        device_type=constants.DEVICE_TYPE,
    )


def create_measurement_group(data: SeriesData) -> MeasurementGroup:
    # This function will be called for every row in the dataset, use it to create
    # a corresponding measurement group.
    return MeasurementGroup(
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=constants.EPOCH_STR,
                sample_identifier=data[str, "Well Name"],
                viability=data[float, "Viability"],
                total_cell_count=data.get(float, "Total Count"),
                total_cell_density=data.get(float, "Total Cells/mL"),
                average_total_cell_diameter=data.get(float, "Total Mean Size"),
                viable_cell_count=data.get(float, "Live Count"),
                viable_cell_density=data[float, "Live Cells/mL"],
                average_live_cell_diameter=data.get(float, "Live Mean Size"),
                dead_cell_count=data.get(float, "Dead Count"),
                dead_cell_density=data.get(float, "Dead Cells/mL"),
                average_dead_cell_diameter=data.get(float, "Dead Mean Size"),
            )
        ]
    )
