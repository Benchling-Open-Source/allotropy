import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import NaN
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_measurement(row: SeriesData, absorbance_col: str) -> Measurement:
    return Measurement(
        type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
        identifier=random_uuid_str(),
        sample_identifier=row[(str, "Sample Name")],
        absorbance=row.get(float, absorbance_col, NaN),
        baseline_absorbance=row.get(float, "Baseline Absorbance"),
    )


def create_measurement_groups(data: dict[str, pd.DataFrame]) -> list[MeasurementGroup]:
    sheet_name = next(iter(data.keys()))  # question: is there always only one sheet
    sheet = data[sheet_name]

    experiment_type, *_ = sheet_name.split(maxsplit=1)

    return [
        MeasurementGroup(
            measurements=[
                create_measurement(SeriesData(row), "A260"),
                create_measurement(SeriesData(row), "A280"),
            ],
            measurement_time=row["Date"],
            experiment_type=experiment_type,
        )
        for _, row in sheet.iterrows()
    ]


def create_data(data: dict[str, pd.DataFrame], file_name: str) -> Data:
    return Data(
        metadata=Metadata(
            device_identifier="N/A",
            device_type="absorbance detector",
            model_number="NanoDrop One",
            brand_name="NanoDrop",
            product_manufacturer="ThermoFisher Scientific",
            file_name=file_name,
            software_name="NanoDrop One software",
        ),
        measurement_groups=create_measurement_groups(data),
    )
