from __future__ import annotations

from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.beckman_vi_cell_blu.constants import (
    DEFAULT_ANALYST,
    DEFAULT_MODEL_NUMBER,
    DETECTION_TYPE,
    DEVICE_TYPE,
    VICELL_BLU_SOFTWARE_NAME,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_measurement_group(data: SeriesData) -> MeasurementGroup:
    total_cell_count = data.get(float, "Cell count")
    total_cell_count = (
        total_cell_count if total_cell_count is None else round(total_cell_count)
    )
    viable_cell_count = data.get(float, "Viable cells")
    viable_cell_count = (
        viable_cell_count if viable_cell_count is None else round(viable_cell_count)
    )

    return MeasurementGroup(
        analyst=data.get(str, "Analysis by", DEFAULT_ANALYST),
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=data[str, "Analysis date/time"],
                sample_identifier=data[str, "Sample ID"],
                cell_type_processing_method=data.get(str, "Cell type"),
                minimum_cell_diameter_setting=data.get(float, "Minimum Diameter (μm)"),
                maximum_cell_diameter_setting=data.get(float, "Maximum Diameter (μm)"),
                cell_density_dilution_factor=data.get(float, "Dilution"),
                viability=data[float, "Viability (%)"],
                viable_cell_density=data[float, "Viable (x10^6) cells/mL"],
                total_cell_count=total_cell_count,
                total_cell_density=data.get(float, "Total (x10^6) cells/mL"),
                average_total_cell_diameter=data.get(float, "Average diameter (μm)"),
                average_live_cell_diameter=data.get(
                    float, "Average viable diameter (μm)"
                ),
                viable_cell_count=viable_cell_count,
                average_total_cell_circularity=data.get(float, "Average circularity"),
                average_viable_cell_circularity=data.get(
                    float, "Average viable circularity"
                ),
            )
        ],
    )


def create_metadata(file_name: str) -> Metadata:
    return Metadata(
        device_type=DEVICE_TYPE,
        detection_type=DETECTION_TYPE,
        model_number=DEFAULT_MODEL_NUMBER,
        software_name=VICELL_BLU_SOFTWARE_NAME,
        file_name=file_name,
    )
