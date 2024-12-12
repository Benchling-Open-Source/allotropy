from decimal import Decimal
from pathlib import Path

from allotropy.allotrope.schema_mappers.adm.cell_counting.rec._2024._09.cell_counting import (
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.chemometec_nc_view import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none


def create_metadata(data: SeriesData, file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_id=NOT_APPLICABLE,
        device_identifier=NOT_APPLICABLE,
        file_name=path.name,
        unc_path=file_path,
        software_name=constants.SOFTWARE_NAME,
        device_type=constants.DEVICE_TYPE,
        equipment_serial_number=data[str, "INSTRUMENT"].split(":")[-1].strip(),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        detection_type=constants.DETECTION_TYPE,
        model_number=NOT_APPLICABLE,
    )


def create_measurement_groups(data: SeriesData) -> MeasurementGroup:
    # Cell counts are measured in cells/mL, but reported in millions of cells/mL
    viable_cell_density = float(
        Decimal(_format_unit(data[str, "LIVE (cells/ml)"])) / Decimal("1000000")
    )
    total_cell_density_val = data.get(str, "TOTAL (cells/ml)")
    if total_cell_density_val:
        total_cell_density = float(
            Decimal(_format_unit(total_cell_density_val)) / Decimal("1000000")
        )
    dead_cell_density_val = data.get(str, "DEAD (cells/ml)")
    if dead_cell_density_val:
        dead_cell_density = float(
            Decimal(_format_unit(dead_cell_density_val)) / Decimal("1000000")
        )

    return MeasurementGroup(
        analyst=data[str, "OPERATOR"],
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                processed_data_identifier=random_uuid_str(),
                timestamp=_format_timestamp(data[str, "NAME"]),
                sample_identifier=data[str, "SAMPLE ID"],
                viability=data[float, "VIABILITY (%)"],
                total_cell_density=total_cell_density,
                viable_cell_density=viable_cell_density,
                dead_cell_density=dead_cell_density,
                average_total_cell_diameter=try_float_or_none(
                    data.get(str, "DIAMETER (μm)")
                ),
                cell_aggregation_percentage=try_float_or_none(
                    data.get(str, "AGGREGATES (%)")
                ),
                debris_index=data.get(float, "DEBRIS INDEX"),
                cell_density_dilution_factor=data.get(float, "DILUTION FACTOR"),
            )
        ],
    )


def _format_unit(unit: str) -> float:
    return float("".join(unit.split()))


def _format_timestamp(timestamp: str) -> str:
    return timestamp.split("-")[0]
