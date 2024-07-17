from __future__ import annotations

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.beckman_vi_cell_blu.constants import (
    DEFAULT_ANALYST,
    DEFAULT_MODEL_NUMBER,
    VICELL_BLU_SOFTWARE_NAME,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def _create_measurement_group(series: pd.Series[str]) -> MeasurementGroup:
    data = SeriesData(series)
    total_cell_count = data.get(float, "Cell count", None)
    total_cell_count = (
        total_cell_count if total_cell_count is None else round(total_cell_count)
    )
    viable_cell_count = data.get(float, "Viable cells", None)
    viable_cell_count = (
        viable_cell_count if viable_cell_count is None else round(viable_cell_count)
    )

    return MeasurementGroup(
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=data[str, "Analysis date/time"],
                sample_identifier=data[str, "Sample ID"],
                cell_type_processing_method=data.get(str, "Cell type", None),
                minimum_cell_diameter_setting=data.get(
                    float, "Minimum Diameter (μm)", None
                ),
                maximum_cell_diameter_setting=data.get(
                    float, "Maximum Diameter (μm)", None
                ),
                cell_density_dilution_factor=data.get(float, "Dilution", None),
                viability=data[float, "Viability (%)"],
                viable_cell_density=data[float, "Viable (x10^6) cells/mL"],
                total_cell_count=total_cell_count,
                total_cell_density=data.get(float, "Total (x10^6) cells/mL", None),
                average_total_cell_diameter=data.get(
                    float, "Average diameter (μm)", None
                ),
                average_live_cell_diameter=data.get(
                    float, "Average viable diameter (μm)", None
                ),
                viable_cell_count=viable_cell_count,
                average_total_cell_circularity=data.get(
                    float, "Average circularity", None
                ),
                average_viable_cell_circularity=data.get(
                    float, "Average viable circularity", None
                ),
                analyst=data.get(str, "Analysis by", DEFAULT_ANALYST),
            )
        ]
    )


def _create_measurement_groups(data: pd.DataFrame) -> list[MeasurementGroup]:
    return list(
        data.apply(
            _create_measurement_group, axis="columns"
        )  # type:ignore[call-overload]
    )


def create_data(data: pd.DataFrame) -> Data:
    metadata = Metadata(
        device_type="brightfield imager (cell counter)",
        detection_type="brightfield",
        model_number=DEFAULT_MODEL_NUMBER,
        software_name=VICELL_BLU_SOFTWARE_NAME,
    )

    return Data(metadata, _create_measurement_groups(data))
