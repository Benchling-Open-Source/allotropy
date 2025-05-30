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


def create_metadata(file_path: str, headers: SeriesData) -> Metadata:
    path = Path(file_path)
    return Metadata(
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_id=NOT_APPLICABLE,
        device_identifier=NOT_APPLICABLE,
        file_name=path.name,
        unc_path=file_path,
        device_type=constants.DEVICE_TYPE,
        software_name="Revvity Matrix",
        software_version=headers.get(str, "Version"),
        equipment_serial_number=headers.get(str, "Instrument SN"),
    )


def create_measurement_group(data: SeriesData, headers: SeriesData) -> MeasurementGroup:
    # This function will be called for every row in the dataset, use it to create
    # a corresponding measurement group.

    viable_cell_density = data[float, ["Live Concentration (E6)", "Live Cells/mL"]]
    # Live Cells/mL needs to be converted to 10^6 cells/mL
    if not data.has_key("Live Concentration (E6)"):
        viable_cell_density = float(Decimal(viable_cell_density) / Decimal("1000000"))

    total_cell_density = data.get(float, ["Total Concentration (E6)", "Total Cells/mL"])
    # Total Cells/mL needs to be converted to 10^6 cells/mL
    if total_cell_density is not None and not data.has_key("Total Concentration (E6)"):
        total_cell_density = float(Decimal(total_cell_density) / Decimal("1000000"))

    dead_cell_density = data.get(float, ["Dead Concentration (E6)", "Dead Cells/mL"])
    # Dead Cells/mL needs to be converted to 10^6 cells/mL
    if dead_cell_density is not None and not data.has_key("Dead Concentration (E6)"):
        dead_cell_density = float(Decimal(dead_cell_density) / Decimal("1000000"))

    errors = data.get(str, ["Errors:", "Errors"], validate=SeriesData.NOT_NAN)

    return MeasurementGroup(
        analyst=headers.get(str, "Operator"),
        custom_info={
            "assay identifier": headers.get(str, "Assay Name"),
        },
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                # NOTE: instrument file does not provide a timestamp, but it is required by ASM, so pass
                # EPOCH to signal no timestamp.
                timestamp=headers.get(
                    str, "Results Timestamp", default=DEFAULT_EPOCH_TIMESTAMP
                ),
                sample_identifier=data[str, "Well Name"],
                viability=data[float, ["Viability", "Viability (%)"]],
                total_cell_count=data.get(float, "Total Count"),
                total_cell_density=total_cell_density,
                average_total_cell_diameter=data.get(
                    float, ["Total Mean Size", "Total Diameter"]
                ),
                viable_cell_count=data.get(float, "Live Count"),
                viable_cell_density=viable_cell_density,
                average_live_cell_diameter=data.get(
                    float, ["Live Mean Size", "Live Diameter"]
                ),
                dead_cell_count=data.get(float, "Dead Count"),
                dead_cell_density=dead_cell_density,
                average_dead_cell_diameter=data.get(
                    float, ["Dead Mean Size", "Dead Diameter"]
                ),
                errors=[
                    Error(error=error, feature="Cell Counting")
                    for error in (errors.split(",") if errors else [])
                ],
                sample_custom_info={
                    "Row": data.get(str, "Row"),
                    "Column": data.get(str, "Column"),
                    "Well Plate Identifier": headers.get(str, "Plate Name"),
                },
                processed_data_identifier=random_uuid_str(),
                cell_aggregation_percentage=data.get(float, "Aggregates (%)"),
                aggregate_count=data.get(float, "Aggregate Count"),
                aggregate_size=data.get(float, "Aggregate Size"),
                cell_density_dilution_factor=headers.get(float, "Dilution"),
                custom_info={
                    "Scanresult Timestamp": headers.get(str, "Scanresult Timestamp"),
                    **(data.get_unread()),
                    **(headers.get_unread()),
                },
            )
        ],
    )
