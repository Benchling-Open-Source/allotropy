import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import NaN
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    CalculatedDataItem,
    Data,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
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
        electronic_absorbance_reference_wavelength_setting=row.get(
            float, "Baseline Correction (nm)"
        ),  # question: is this correct, always (nm)
        nucleic_acid_factor=row.get(float, "Nucleic Acid Factor"),
        detector_wavelength_setting=0,  # question: how to obtain
        processed_data=ProcessedData(
            features=[
                ProcessedDataFeature(
                    result=row.get(float, "Nucleic Acid(ng/uL)", NaN),
                    unit="ng/uL",  # question: how to know the unit
                )
            ],
        ),
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


def get_calculated_data_element(
    row: SeriesData, column: str
) -> CalculatedDataItem | None:
    value = row.get(float, column)
    if value is None:
        return None

    return CalculatedDataItem(
        identifier=random_uuid_str(),
        name=column,
        value=value,
        unit=UNITLESS,
        data_sources=[],
    )


def create_calculated_data(data: dict[str, pd.DataFrame]) -> list[CalculatedDataItem]:
    sheet_name = next(iter(data.keys()))  # question: is there always only one sheet
    sheet = data[sheet_name]

    calculated_data = []
    for _, row in sheet.iterrows():
        if a260_a230 := get_calculated_data_element(SeriesData(row), "A260/A230"):
            calculated_data.append(a260_a230)

        if a260_a280 := get_calculated_data_element(SeriesData(row), "A260/A280"):
            calculated_data.append(a260_a280)

    return calculated_data


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
        calculated_data=create_calculated_data(data),
    )
