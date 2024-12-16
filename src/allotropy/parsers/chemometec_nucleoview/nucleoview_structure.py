from __future__ import annotations

from pathlib import Path

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.cell_counting.rec._2024._09.cell_counting import (
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.chemometec_nucleoview.constants import (
    DEFAULT_ANALYST,
    DEFAULT_MODEL_NUMBER,
    NUCLEOCOUNTER_DETECTION_TYPE,
    NUCLEOCOUNTER_DEVICE_TYPE,
    NUCLEOCOUNTER_SOFTWARE_NAME,
)
from allotropy.parsers.constants import (
    DEFAULT_EPOCH_TIMESTAMP,
    NEGATIVE_ZERO,
    NOT_APPLICABLE,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(data: SeriesData, file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_id=data.get(str, "PC", NOT_APPLICABLE),
        file_name=Path(file_path).name,
        unc_path=file_path,
        model_number=data.get(str, "Instrument type", DEFAULT_MODEL_NUMBER),
        equipment_serial_number=data.get(str, "Instrument s/n"),
        software_name=NUCLEOCOUNTER_SOFTWARE_NAME,
        software_version=data.get(str, "Application SW version"),
        device_type=NUCLEOCOUNTER_DEVICE_TYPE,
        detection_type=NUCLEOCOUNTER_DETECTION_TYPE,
    )


def create_measurement_groups(data: SeriesData) -> MeasurementGroup:
    timestamp = data.get(str, "Date time")
    errors = []
    if timestamp:
        offset = data.get(str, "Time zone offset", "0")
        timestamp = pd.to_datetime(
            f"{timestamp}{'+' if offset[0] not in {'+', '-'} else ''}{offset}"
        ).isoformat()

    def _converted_value_or_none(key: str) -> float | None:
        return value / 1e6 if (value := data.get(float, key)) is not None else None

    viable_cell_density = data.get(float, "Live (cells/ml)")
    if viable_cell_density is None:
        errors.append(
            Error(
                error=NOT_APPLICABLE,
                feature="viable cell density",
            )
        )
    return MeasurementGroup(
        analyst=data.get(str, "Operator", DEFAULT_ANALYST),
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=timestamp or DEFAULT_EPOCH_TIMESTAMP,
                sample_identifier=data[str, "Image"].split("-")[3],
                cell_density_dilution_factor=data.get(float, "Multiplication factor"),
                viability=data[float, "Viability (%)"],
                # Cell counts are measured in cells/mL, but reported in millions of cells/mL
                viable_cell_density=(viable_cell_density / 1e6)
                if viable_cell_density
                else NEGATIVE_ZERO,
                dead_cell_density=_converted_value_or_none("Dead (cells/ml)"),
                total_cell_density=_converted_value_or_none("Total (cells/ml)"),
                average_total_cell_diameter=data.get(
                    float, "Estimated cell diameter (um)"
                ),
                errors=errors,
            )
        ],
    )
