from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    DataCube,
    DataCubeComponent,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import DEFAULT_EPOCH_TIMESTAMP, NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_visionlite.constants import (
    DETECTION_TYPE,
    DEVICE_TYPE,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
    UNSUPPORTED_KINETIC_MEASUREMENTS_ERROR,
)
from allotropy.parsers.thermo_fisher_visionlite.thermo_fisher_visionlite_reader import (
    ThermoFisherVisionliteReader,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none


class ExperimentType(Enum):
    SCAN = "Scan"
    QUANT = "Quant"
    FIXED = "Fixed"

    @property
    def measurement_type(self) -> MeasurementType:
        return _EXPERIMENT_TO_MEASUREMENT_TYPE[self]


_EXPERIMENT_TO_MEASUREMENT_TYPE = {
    ExperimentType.FIXED: MeasurementType.ULTRAVIOLET_ABSORBANCE,
    ExperimentType.QUANT: MeasurementType.ULTRAVIOLET_ABSORBANCE,
    ExperimentType.SCAN: MeasurementType.ULTRAVIOLET_ABSORBANCE_SPECTRUM,
}


def _get_experiment_type(reader: ThermoFisherVisionliteReader) -> ExperimentType:
    if reader.header:
        if "nm" in reader.data.columns:
            return ExperimentType.SCAN
        else:
            raise AllotropeConversionError(UNSUPPORTED_KINETIC_MEASUREMENTS_ERROR)
    elif "Dilution factor" in reader.data.columns:
        return ExperimentType.QUANT
    else:
        return ExperimentType.FIXED


@dataclass(frozen=True)
class Header:
    sample_name: str | None = None
    analyst: str | None = None
    measurement_time: str = DEFAULT_EPOCH_TIMESTAMP

    @staticmethod
    def create(header_data: SeriesData | None) -> Header:
        if header_data is None:
            return Header()

        return Header(
            sample_name=header_data[str, "Sample Name"],
            analyst=header_data[str, "Analyst"],
            measurement_time=header_data[str, "Measurement Time"],
        )


@dataclass(frozen=True)
class AbsorbanceMeasurement:
    absorbance: float
    wavelength: int | None = None


def create_metadata(file_path: str) -> Metadata:
    return Metadata(
        file_name=Path(file_path).name,
        unc_path=file_path,
        device_identifier=NOT_APPLICABLE,
        device_type=DEVICE_TYPE,
        model_number=NOT_APPLICABLE,
        software_name=SOFTWARE_NAME,
        detection_type=DETECTION_TYPE,
        product_manufacturer=PRODUCT_MANUFACTURER,
    )


def create_measurement_groups(
    reader: ThermoFisherVisionliteReader,
) -> list[MeasurementGroup]:
    experiment_type = _get_experiment_type(reader)
    header = Header.create(reader.header)
    return _get_measurement_groups(reader.data, header, experiment_type)


def _get_measurement_groups(
    data: pd.DataFrame, header: Header, experiment_type: ExperimentType
) -> list[MeasurementGroup]:
    if experiment_type == ExperimentType.SCAN:
        if header.sample_name is None:
            msg = "Missing Sample Name."
            raise AllotropeConversionError(msg)
        return [
            MeasurementGroup(
                analyst=header.analyst,
                measurement_time=header.measurement_time,
                experiment_type=experiment_type.value,
                measurements=[
                    Measurement(
                        type_=experiment_type.measurement_type,
                        identifier=random_uuid_str(),
                        sample_identifier=header.sample_name,
                        data_cube=_get_data_cube(data),
                    )
                ],
            )
        ]

    return [
        MeasurementGroup(
            analyst=header.analyst,
            measurement_time=header.measurement_time,
            experiment_type=experiment_type.value,
            measurements=_get_absorbance_measurements(row, experiment_type),
        )
        for _, row in data.iterrows()
    ]


def _get_absorbance_measurements(
    row: pd.Series[Any], experiment_type: ExperimentType
) -> list[Measurement]:
    data = SeriesData(row)
    if experiment_type == ExperimentType.QUANT:
        ordinate_col = "Ordinate [A]"
        if not data.has_key(ordinate_col):
            msg = "Unable to determine Quant absorbance measurements, Ordinate column missing."
            raise AllotropeConversionError(msg)
        absorbance_measurements = [
            AbsorbanceMeasurement(absorbance=data[float, ordinate_col])
        ]
    elif experiment_type == ExperimentType.FIXED:
        if not (wavelengths := _get_wavelengths(list(data.series.index))):
            msg = "Only Fixed absorbance measurements are supported at this time."
        absorbance_measurements = [
            AbsorbanceMeasurement(
                absorbance=data[float, f"{wavelength} nm   [A]"],
                wavelength=wavelength,
            )
            for wavelength in wavelengths
        ]

    return [
        Measurement(
            type_=experiment_type.measurement_type,
            identifier=random_uuid_str(),
            sample_identifier=data[str, "Sample Name"],
            processed_data=(
                _get_processed_data(data)
                if experiment_type == ExperimentType.QUANT
                else None
            ),
            absorbance=measurement.absorbance,
            dilution_factor_setting=data.get(float, "Dilution factor"),
            detector_wavelength_setting=try_float_or_none(measurement.wavelength),
        )
        for measurement in absorbance_measurements
    ]


def _get_processed_data(data: SeriesData) -> ProcessedData:
    concentration_unit = _get_concentration_unit(list(data.series.index))

    concentration_col = f"Concentration [{concentration_unit}]"
    if not data.has_key(concentration_col):
        msg = "Unable to find Concentration data."
        raise AllotropeConversionError(msg)

    return ProcessedData(
        identifier=random_uuid_str(),
        features=[
            ProcessedDataFeature(
                result=data[float, concentration_col],
                unit=concentration_unit,
            )
        ],
    )


def _get_concentration_unit(columns: list[str]) -> str:
    for col in columns:
        if match := re.match(r"Concentration \[(.*)\]", col):
            return match.groups()[0]
    return ""


def _get_wavelengths(columns: list[str]) -> list[int]:
    wavelengths = []
    for col in columns:
        if match := re.match(r"(\d{1,}) nm   \[A\]", col):
            wavelengths.append(int(match.groups()[0]))
    return wavelengths


def _get_data_cube(data: pd.DataFrame) -> DataCube:
    return DataCube(
        label="absorption spectrum",
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double,
                concept="wavelength",
                unit="nm",
            )
        ],
        structure_measures=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double,
                concept="absorbance",
                unit="mAU",
            )
        ],
        dimensions=[data["nm"].to_list()],
        measures=[data["A"].to_list()],
    )
