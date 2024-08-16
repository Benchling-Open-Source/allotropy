from __future__ import annotations

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    NaN,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.benchling._2023._11.cell_counting import (
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.chemometec_nucleoview.constants import (
    DEFAULT_ANALYST,
    DEFAULT_EPOCH_TIMESTAMP,
    DEFAULT_MODEL_NUMBER,
    NUCLEOCOUNTER_DETECTION_TYPE,
    NUCLEOCOUNTER_DEVICE_TYPE,
    NUCLEOCOUNTER_SOFTWARE_NAME,
)
from allotropy.parsers.chemometec_nucleoview.nucleoview_reader import NucleoviewReader
from allotropy.parsers.utils.pandas import df_to_series_data, map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def _create_metadata(data: SeriesData, file_name: str) -> Metadata:
    return Metadata(
        file_name=file_name,
        model_number=data.get(str, "Instrument type", DEFAULT_MODEL_NUMBER),
        equipment_serial_number=data.get(str, "Instrument s/n"),
        software_name=NUCLEOCOUNTER_SOFTWARE_NAME,
        software_version=data.get(str, "Application SW version"),
        device_type=NUCLEOCOUNTER_DEVICE_TYPE,
        detection_type=NUCLEOCOUNTER_DETECTION_TYPE,
    )


def _create_measurement_groups(data: SeriesData) -> MeasurementGroup:
    timestamp = data.get(str, "Date time")
    if timestamp:
        offset = data.get(str, "Time zone offset", "0")
        timestamp = pd.to_datetime(
            f"{timestamp}{'+' if offset[0] not in {'+', '-'} else ''}{offset}"
        ).isoformat()

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
                viable_cell_density=data.get(float, "Live (cells/ml)", NaN) / 1e6,
                dead_cell_density=data.get(float, "Dead (cells/ml)", NaN) / 1e6,
                total_cell_density=data.get(float, "Total (cells/ml)", NaN) / 1e6,
                average_total_cell_diameter=data.get(
                    float, "Estimated cell diameter (um)", NaN
                ),
            )
        ],
    )


def create_data(named_file_contents: NamedFileContents) -> Data:
    df = NucleoviewReader.read(named_file_contents.contents)
    return Data(
        _create_metadata(
            df_to_series_data(df.head(1), "Unable to parse row in dataset."),
            named_file_contents.original_file_name,
        ),
        map_rows(df, _create_measurement_groups),
    )
