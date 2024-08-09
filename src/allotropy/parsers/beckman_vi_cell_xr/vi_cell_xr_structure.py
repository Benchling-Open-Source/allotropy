from __future__ import annotations

from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import (
    AllotropeConversionError,
)
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DEFAULT_ANALYST,
    MODEL_NUMBER,
    SOFTWARE_NAME,
)
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import ViCellData
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def _create_measurement_group(data: SeriesData) -> MeasurementGroup:
    total_cell_count = data.get(float, "Total cells")
    total_cell_count = (
        total_cell_count if total_cell_count is None else round(total_cell_count)
    )
    viable_cell_count = data.get(float, "Viable cells")
    viable_cell_count = (
        viable_cell_count if viable_cell_count is None else round(viable_cell_count)
    )

    return MeasurementGroup(
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=data[str, "Sample date"],
                sample_identifier=data[str, "Sample ID"],
                cell_type_processing_method=data.get(str, "Cell type"),
                cell_density_dilution_factor=data.get(float, "Dilution factor"),
                viability=data[float, "Viability (%)"],
                viable_cell_density=data[float, "Viable cells/ml (x10^6)"],
                total_cell_count=total_cell_count,
                total_cell_density=data.get(float, "Total cells/ml (x10^6)"),
                average_total_cell_diameter=data.get(float, "Avg. diam. (microns)"),
                viable_cell_count=viable_cell_count,
                average_total_cell_circularity=data.get(float, "Avg. circ."),
                analyst=DEFAULT_ANALYST,
            )
        ]
    )


def create_data(reader_data: ViCellData, file_name: str) -> Data:
    if not reader_data.data:
        msg = "Cannot parse ASM from empty file."
        raise AllotropeConversionError(msg)

    metadata = Metadata(
        device_type="brightfield imager (cell counter)",
        detection_type="brightfield",
        model_number=MODEL_NUMBER,
        equipment_serial_number=reader_data.serial_number,
        software_name=SOFTWARE_NAME,
        software_version=reader_data.version.value,
        file_name=file_name,
    )

    return Data(metadata, [_create_measurement_group(row) for row in reader_data.data])
