from __future__ import annotations

from pathlib import Path

import pandas as pd

from allotropy.allotrope.models.shared.definitions.units import (
    Micrometer,
    Percent,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.rec._2024._09.cell_counting import (
    CalculatedDataItem,
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.chemometec_nucleoview.constants import (
    DEFAULT_ANALYST,
    DEFAULT_MODEL_NUMBER,
    MEASUREMENT_AGG_DOCUMENT_CUSTOM_FIELDS,
    NUCLEOCOUNTER_DETECTION_TYPE,
    NUCLEOCOUNTER_DEVICE_TYPE,
    NUCLEOCOUNTER_SOFTWARE_NAME,
)
from allotropy.parsers.constants import (
    DEFAULT_EPOCH_TIMESTAMP,
    NEGATIVE_ZERO,
    NOT_APPLICABLE,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(data: SeriesData, file_path: str) -> Metadata:
    path = Path(file_path)
    metadata = Metadata(
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
        data_system_custom_info=data.get_custom_keys(
            {
                "csv file version",
                "21 CFR Part 11",
            }
        ),
    )
    # We read header info from a row in the table, so we don't need to read all keys from this SeriesData
    data.get_unread()
    return metadata


def create_measurement_groups(
    data: SeriesData,
) -> tuple[MeasurementGroup, list[CalculatedDataItem] | None]:
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
    # These fields we read from the first row as metadata, so we don't need to read them here
    data.mark_read(
        {
            "PC",
            "Instrument type",
            "Instrument s/n",
            "Application SW version",
            "21 CFR Part 11",
            "csv file version",
        }
    )
    percentage_of_cells_with_five_or_more = data.get(
        float, "(%) of cells in aggregates with five or more cells"
    )
    cell_diameter_standard_deviation = data.get(
        float, "Cell diameter standard deviation (um)"
    )
    measurement_group = MeasurementGroup(
        analyst=data.get(str, "Operator", DEFAULT_ANALYST),
        custom_info=data.get_custom_keys(MEASUREMENT_AGG_DOCUMENT_CUSTOM_FIELDS),
        measurements=[
            Measurement(
                measurement_identifier=random_uuid_str(),
                timestamp=timestamp or DEFAULT_EPOCH_TIMESTAMP,
                sample_identifier=data.get(str, "Sample ID")
                or data[str, "Image"].split("-")[3],
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
                sample_volume_setting=data.get(float, "Sample Volume (ul)"),
                experimental_data_identifier=data.get(str, "cm filename"),
                dilution_volume=data.get(float, "Dilution Volume (ul)"),
                custom_info=data.get_unread(),
            )
        ],
    )

    return measurement_group, _get_calculated_data(
        [measurement_group],
        cell_diameter_standard_deviation,
        percentage_of_cells_with_five_or_more,
    )


def _get_calculated_data(
    groups: list[MeasurementGroup],
    cell_diameter_standard_deviation: float | None,
    percentage_of_cells_with_five_or_more: float | None,
) -> list[CalculatedDataItem] | None:
    result = []
    for group in groups:
        if cell_diameter_standard_deviation:
            result.append(
                CalculatedDataItem(
                    identifier=random_uuid_str(),
                    name="Cell diameter standard deviation (um)",
                    value=cell_diameter_standard_deviation,
                    data_sources=[
                        DataSource(
                            feature="Average Total Cell Diameter",
                            reference=Referenceable(
                                uuid=group.measurements[0].measurement_identifier
                            ),
                        )
                    ],
                    unit=Micrometer.unit,
                )
            )
        if percentage_of_cells_with_five_or_more:
            result.append(
                CalculatedDataItem(
                    identifier=random_uuid_str(),
                    name="Percentage of cells with five or more",
                    value=percentage_of_cells_with_five_or_more,
                    data_sources=[
                        DataSource(
                            feature="Cell count",
                            reference=Referenceable(
                                uuid=group.measurements[0].measurement_identifier
                            ),
                        )
                    ],
                    unit=Percent.unit,
                )
            )
    return result
