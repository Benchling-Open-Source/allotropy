from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import DEFAULT_EPOCH_TIMESTAMP, NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_visionlite.constants import (
    DETECTION_TYPE,
    DEVICE_TYPE,
    PRODUCT_MANUFACTURER,
    SAMPLE_NAME_COLS,
    SOFTWARE_NAME,
    UNSUPPORTED_KINETIC_MEASUREMENTS_ERROR,
)
from allotropy.parsers.thermo_fisher_visionlite.thermo_fisher_visionlite_reader import (
    ThermoFisherVisionliteReader,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_none,
    try_int_or_none,
)


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
            sample_name=header_data[str, ("Sample Name", "Well Position")],
            analyst=header_data[str, "Analyst"],
            measurement_time=header_data[str, "Measurement Time"],
        )


@dataclass(frozen=True)
class AbsorbanceMeasurement:
    absorbance: float
    wavelength: int | None = None


class VisionLiteData(Data):
    @staticmethod
    def create(
        reader: ThermoFisherVisionliteReader,
        file_path: str,
        software_name: str = SOFTWARE_NAME,
    ) -> Data:
        experiment_type = _get_experiment_type(reader)
        header = Header.create(reader.header)
        data = reader.data
        measurement_groups = []
        calculated_data = []

        if experiment_type == ExperimentType.SCAN:
            if header.sample_name is None:
                msg = "Missing Sample Name."
                raise AllotropeConversionError(msg)
            measurement_groups = [
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
        else:
            wavelength_cols = _get_wavelength_cols(list(data.columns))
            for _, row in data.iterrows():
                row_data = SeriesData(row)
                measurements = _get_absorbance_measurements(
                    row_data, experiment_type, wavelength_cols
                )
                measurement_groups.append(
                    MeasurementGroup(
                        analyst=header.analyst,
                        measurement_time=header.measurement_time,
                        experiment_type=experiment_type.value,
                        measurements=measurements,
                    )
                )
                if result := row_data.get(float, "Result"):
                    calculated_data.append(
                        _get_calculated_data_item(result, measurements)
                    )

        return Data(
            metadata=_create_metadata(file_path, software_name),
            measurement_groups=measurement_groups,
            calculated_data=calculated_data,
        )


def _get_calculated_data_item(
    result: float, measurements: list[Measurement]
) -> CalculatedDocument:
    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="Result",
        value=result,
        unit=UNITLESS,
        data_sources=[
            DataSource(
                feature="Absorbance",
                reference=Referenceable(uuid=measurement.identifier),
            )
            for measurement in measurements
        ],
    )


def _create_metadata(file_path: str, software_name: str) -> Metadata:
    return Metadata(
        file_name=Path(file_path).name,
        unc_path=file_path,
        device_identifier=NOT_APPLICABLE,
        device_type=DEVICE_TYPE,
        model_number=NOT_APPLICABLE,
        software_name=software_name,
        detection_type=DETECTION_TYPE,
        product_manufacturer=PRODUCT_MANUFACTURER,
    )


def _get_absorbance_measurements(
    data: SeriesData,
    experiment_type: ExperimentType,
    wavelength_cols: dict[int, str],
) -> list[Measurement]:
    if experiment_type == ExperimentType.QUANT:
        ordinate_col = "Ordinate [A]"
        if not data.has_key(ordinate_col):
            msg = "Unable to determine Quant absorbance measurements, Ordinate column missing."
            raise AllotropeConversionError(msg)
        absorbance_measurements = [
            AbsorbanceMeasurement(absorbance=data[float, ordinate_col])
        ]
    elif experiment_type == ExperimentType.FIXED:
        if wavelength_cols:
            absorbance_measurements = [
                AbsorbanceMeasurement(
                    absorbance=data[float, col],
                    wavelength=wavelength,
                )
                for wavelength, col in wavelength_cols.items()
            ]
        else:
            absorbance_measurements = [
                AbsorbanceMeasurement(absorbance=data[float, "Absorbance"])
            ]

    return [
        Measurement(
            type_=experiment_type.measurement_type,
            identifier=random_uuid_str(),
            sample_identifier=data[str, SAMPLE_NAME_COLS],
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


def _get_wavelength_cols(columns: list[str]) -> dict[int, str]:
    wavelength_cols = {}
    for col in columns:
        if match := re.match(r"(\d{1,}) nm   \[A\]|A(\d{1,})", col):
            wavelength = assert_not_none(
                get_first_not_none(try_int_or_none, match.groups())
            )
            wavelength_cols[wavelength] = col
    return wavelength_cols


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
