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
    total_cell_count = data.try_float_or_none("Cell count")
    total_cell_count = (
        total_cell_count if total_cell_count is None else round(total_cell_count)
    )
    viable_cell_count = data.try_float_or_none("Viable cells")
    viable_cell_count = (
        viable_cell_count if viable_cell_count is None else round(viable_cell_count)
    )

    return MeasurementGroup(
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=data.try_str("Analysis date/time"),
                sample_identifier=data.try_str("Sample ID"),
                cell_type_processing_method=data.try_str_or_none("Cell type"),
                minimum_cell_diameter_setting=data.try_float_or_none("Minimum Diameter (μm)"),
                maximum_cell_diameter_setting=data.try_float_or_none("Maximum Diameter (μm)"),
                cell_density_dilution_factor=data.try_float_or_none("Dilution"),
                viability=data.try_float("Viability (%)"),
                viable_cell_density=data.try_float("Viable (x10^6) cells/mL"),
                total_cell_count=total_cell_count,
                total_cell_density=data.try_float_or_none("Total (x10^6) cells/mL"),
                average_total_cell_diameter=data.try_float_or_none("Average diameter (μm)"),
                average_live_cell_diameter=data.try_float_or_none("Average viable diameter (μm)"),
                viable_cell_count=viable_cell_count,
                average_total_cell_circularity=data.try_float_or_none("Average circularity"),
                average_viable_cell_circularity=data.try_float_or_none("Average viable circularity"),
                analyst=data.try_str_or_none("Analysis by")
                or DEFAULT_ANALYST,
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
