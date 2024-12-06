from __future__ import annotations

from pathlib import Path

from allotropy.allotrope.schema_mappers.adm.cell_counting.rec._2024._09.cell_counting import (
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.beckman_vi_cell_xr.constants import (
    DEFAULT_ANALYST,
    DETECTION_TYPE,
    DEVICE_TYPE,
    MODEL_NUMBER,
    SOFTWARE_NAME,
)
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import ViCellData
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_measurement_group(data: SeriesData) -> MeasurementGroup:
    total_cell_count = data.get(float, "Total cells")
    total_cell_count = (
        total_cell_count if total_cell_count is None else round(total_cell_count)
    )
    viable_cell_count = data.get(float, "Viable cells")
    viable_cell_count = (
        viable_cell_count if viable_cell_count is None else round(viable_cell_count)
    )

    return MeasurementGroup(
        analyst=DEFAULT_ANALYST,
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
            )
        ],
    )


def create_metadata(reader_data: ViCellData, file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        device_type=DEVICE_TYPE,
        detection_type=DETECTION_TYPE,
        model_number=MODEL_NUMBER,
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_id=NOT_APPLICABLE,
        device_identifier=NOT_APPLICABLE,
        equipment_serial_number=reader_data.serial_number,
        software_name=SOFTWARE_NAME,
        software_version=reader_data.version.value,
        file_name=path.name,
        unc_path=file_path,
    )
