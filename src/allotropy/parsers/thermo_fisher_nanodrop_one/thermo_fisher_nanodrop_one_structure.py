from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import NaN
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
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float


@dataclass
class MetadataNanodrop:
    nucleic_acid_unit: str
    absorbance_columns: list[str]
    calculated_columns: list[str]


@dataclass
class InputNanodrop:
    metadata: MetadataNanodrop
    data: list[SeriesData]


@dataclass(frozen=True)
class MeasurementGroupNanodrop(MeasurementGroup):
    @staticmethod
    def create(
        row: SeriesData, metadata: MetadataNanodrop, experiment_type: str
    ) -> MeasurementGroupNanodrop:
        sample_identifier = row[(str, "Sample Name")]
        nucleic_acid = row.get(float, "Nucleic Acid", validate=SeriesData.NOT_NAN)
        baseline_absorbance = row.get(
            float, "Baseline Absorbance", validate=SeriesData.NOT_NAN
        )
        electronic_absorbance_reference_wavelength_setting = row.get(
            float, "Baseline Correction", validate=SeriesData.NOT_NAN
        )
        nucleic_acid_factor = row.get(
            float, "Nucleic Acid Factor", validate=SeriesData.NOT_NAN
        )

        measurements = [
            Measurement(
                type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
                identifier=random_uuid_str(),
                sample_identifier=sample_identifier,
                absorbance=row.get(float, column, NaN),
                baseline_absorbance=baseline_absorbance,
                electronic_absorbance_reference_wavelength_setting=electronic_absorbance_reference_wavelength_setting,
                detector_wavelength_setting=try_float(
                    column.removeprefix("A"),
                    "detector wavelength setting",
                ),
                processed_data=(
                    None
                    if nucleic_acid is None
                    else ProcessedData(
                        features=[
                            ProcessedDataFeature(
                                result=nucleic_acid,
                                unit=metadata.nucleic_acid_unit,
                            )
                        ],
                    )
                ),
                device_control_custom_info={
                    "nucleic acid factor": {
                        "value": nucleic_acid_factor,
                        "unit": UNITLESS,
                    }
                    if nucleic_acid_factor is not None
                    else None
                },
            )
            for column in metadata.absorbance_columns
        ]

        return MeasurementGroupNanodrop(
            measurements=measurements,
            measurement_time=row[str, "Date"],
            experiment_type=experiment_type,
        )

    def get_measurement(self, raw_wavelength: str) -> Measurement | None:
        detector_wavelength_setting = try_float(
            raw_wavelength.removeprefix("A"),
            "detector wavelength setting",
        )
        for measurement in self.measurements:
            if measurement.detector_wavelength_setting == detector_wavelength_setting:
                return measurement
        return None


def create_calculated_data(
    row: SeriesData,
    metadata: MetadataNanodrop,
    measurement_group: MeasurementGroupNanodrop,
) -> list[CalculatedDocument]:
    calculated_data = []
    for column in metadata.calculated_columns:
        value = row.get(float, column)
        if value is None:
            continue

        wavelengths = column.split("/")
        data_sources = []

        for wavelength in wavelengths:
            measurement = measurement_group.get_measurement(wavelength)
            if measurement:
                data_sources.append(
                    DataSource(
                        feature="absorbance",
                        reference=Referenceable(uuid=measurement.identifier),
                    )
                )

        calculated_data.append(
            CalculatedDocument(
                uuid=random_uuid_str(),
                name=column,
                value=value,
                unit=UNITLESS,
                data_sources=data_sources,
            )
        )
    return calculated_data


@dataclass
class RowElements:
    # is not a list to avoid invariance problem
    measurement_groups: tuple[MeasurementGroup, ...]
    calculated_data: list[CalculatedDocument]

    @staticmethod
    def filter_column_names(data: pd.DataFrame, regex: str) -> list[str]:
        return [column for column in data.columns if re.search(regex, column)]

    @staticmethod
    def filter_column_name(data: pd.DataFrame, pattern: str) -> str:
        columns = RowElements.filter_column_names(data, pattern)
        if len(columns) == 1:
            return columns[0]

        error = f"Unable to find column using pattern {pattern}."
        raise AllotropeConversionError(error)

    @staticmethod
    def filter_data(data: pd.DataFrame) -> InputNanodrop:
        nucleic_acid_col = RowElements.filter_column_name(data, r"^Nucleic Acid\s*\(")
        absorbance_columns = RowElements.filter_column_names(data, r"^A(\d{3})$")
        calculated_columns = RowElements.filter_column_names(
            data, r"^A(\d{3})/A(\d{3})$"
        )
        baseline_correction_col = RowElements.filter_column_name(
            data, "^Baseline Correction"
        )

        columns = [
            "Date",
            "Sample Name",
            "Baseline Absorbance",
            "Nucleic Acid Factor",
            baseline_correction_col,
            nucleic_acid_col,
            *absorbance_columns,
            *calculated_columns,
        ]
        new_data = data[columns].rename(
            columns={
                baseline_correction_col: "Baseline Correction",
                nucleic_acid_col: "Nucleic Acid",
            }
        )

        if match := re.match(r".*\((.+)\)", nucleic_acid_col):
            nucleic_acid_unit = match.group(1)
        else:
            error = "Unable to find nucleic acid unit"
            raise AllotropeConversionError(error)

        return InputNanodrop(
            metadata=MetadataNanodrop(
                nucleic_acid_unit,
                absorbance_columns,
                calculated_columns,
            ),
            data=[SeriesData(row) for _, row in new_data.iterrows()],
        )

    @staticmethod
    def create(data: pd.DataFrame, experiment_type: str) -> RowElements:
        clean_data = RowElements.filter_data(data)

        measurement_groups = []
        calculated_data = []
        for row in clean_data.data:
            measurement_group = MeasurementGroupNanodrop.create(
                row, clean_data.metadata, experiment_type
            )
            measurement_groups.append(measurement_group)
            calculated_data += create_calculated_data(
                row, clean_data.metadata, measurement_group
            )
            unread_data = row.get_unread()
            for measurement_group in measurement_groups:
                for measurement in measurement_group.measurements:
                    measurement.custom_info = unread_data
        return RowElements(tuple(measurement_groups), calculated_data)


@dataclass(frozen=True)
class DataNanodrop(Data):
    @staticmethod
    def create(data: pd.DataFrame, experiment_type: str, file_path: str) -> Data:
        row_elements = RowElements.create(data, experiment_type)

        return Data(
            metadata=Metadata(
                device_identifier="N/A",
                device_type="absorbance detector",
                model_number="NanoDrop One",
                brand_name="NanoDrop",
                product_manufacturer="ThermoFisher Scientific",
                file_name=Path(file_path).name,
                unc_path=file_path,
                software_name="NanoDrop One software",
            ),
            measurement_groups=list(row_elements.measurement_groups),
            calculated_data=row_elements.calculated_data or None,
        )
