from decimal import Decimal
from pathlib import Path

from allotropy.allotrope.schema_mappers.adm.cell_counting.rec._2024._09.cell_counting import (
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.constants import DEFAULT_EPOCH_TIMESTAMP, NOT_APPLICABLE
from allotropy.parsers.revvity_matrix import constants
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_id=NOT_APPLICABLE,
        device_identifier=NOT_APPLICABLE,
        file_name=path.name,
        unc_path=file_path,
        device_type=constants.DEVICE_TYPE,
    )


def create_measurement_group(data: SeriesData) -> MeasurementGroup:
    # This function will be called for every row in the dataset, use it to create
    # a corresponding measurement group.

    # Cell counts are measured in cells/mL, but reported in millions of cells/mL
    viable_cell_density = float(
        Decimal(data[float, "Live Cells/mL"]) / Decimal("1000000")
    )
    total_cell_density = data.get(float, "Total Cells/mL")
    if total_cell_density:
        total_cell_density = float(Decimal(total_cell_density) / Decimal("1000000"))
    dead_cell_density = data.get(float, "Dead Cells/mL")
    if dead_cell_density:
        dead_cell_density = float(Decimal(dead_cell_density) / Decimal("1000000"))

    errors = data.get(str, "Errors:", validate=SeriesData.NOT_NAN)
    return MeasurementGroup(
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                # NOTE: instrument file does not provide a timestamp, but it is required by ASM, so pass
                # EPOCH to signal no timestamp.
                timestamp=DEFAULT_EPOCH_TIMESTAMP,
                sample_identifier=data[str, "Well Name"],
                viability=data[float, "Viability"],
                total_cell_count=data.get(float, "Total Count"),
                total_cell_density=total_cell_density,
                average_total_cell_diameter=data.get(float, "Total Mean Size"),
                viable_cell_count=data.get(float, "Live Count"),
                viable_cell_density=viable_cell_density,
                average_live_cell_diameter=data.get(float, "Live Mean Size"),
                dead_cell_count=data.get(float, "Dead Count"),
                dead_cell_density=dead_cell_density,
                average_dead_cell_diameter=data.get(float, "Dead Mean Size"),
                errors=[
                    Error(error=error)
                    for error in (errors.split(",") if errors else [])
                ],
            )
        ]
    )
