from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.solution_analyzer.benchling._2024._09.solution_analyzer import (
    Analyte,
    DataProcessing,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.novabio_flex2.constants import (
    ANALYTE_MAPPINGS,
    DATA_PROCESSING_FIELDS,
    DETECTION_PROPERTY_MAPPING,
    DEVICE_TYPE,
    FILENAME_REGEX,
    INVALID_FILENAME_MESSAGE,
    MODEL_NUMBER,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none


@dataclass(frozen=True)
class Title:
    processing_time: str
    device_identifier: str | None

    @staticmethod
    def create(file_path: str) -> Title:
        filename = Path(file_path).name
        matches = re.match(FILENAME_REGEX, filename, flags=re.IGNORECASE)

        if not matches:
            raise AllotropeConversionError(INVALID_FILENAME_MESSAGE.format(filename))

        matches_dict = matches.groupdict()
        return Title(
            processing_time=matches_dict["processing_time"].replace("_", " "),
            device_identifier=matches_dict["device_identifier"] or None,
        )


@dataclass(frozen=True)
class Sample:
    identifier: str
    sample_type: str
    measurement_time: str
    batch_identifier: str | None
    analytes: list[Analyte]
    po2: float | None = None
    po2_unit: str | None = None
    pco2: float | None = None
    pco2_unit: str | None = None
    carbon_dioxide_saturation: float | None = None
    oxygen_saturation: float | None = None
    ph: float | None = None
    temperature: float | None = None
    osmolality: float | None = None
    viability: float | None = None
    total_cell_density: float | None = None
    total_cell_density_unit: str | None = None
    viable_cell_density: float | None = None
    viable_cell_density_unit: str | None = None
    average_live_cell_diameter: float | None = None
    total_cell_count: float | None = None
    viable_cell_count: float | None = None
    cell_type_processing_method: str | None = None
    cell_density_dilution_factor: float | None = None

    @classmethod
    def create(cls, units: SeriesData, data: SeriesData) -> Sample:
        cell_density_dilution = data.get(str, "Cell Density Dilution", "")
        if cell_density_dilution:
            cell_density_dilution = cell_density_dilution.split(":")[0]

        return Sample(
            identifier=data[str, "Sample ID"],
            sample_type=data[str, "Sample Type"],
            measurement_time=data[str, "Date & Time"],
            batch_identifier=data.get(str, "Batch ID"),
            analytes=sorted(
                [
                    Analyte(
                        ANALYTE_MAPPINGS[raw_name]["name"],
                        data[float, raw_name],
                        units.get(str, raw_name, ANALYTE_MAPPINGS[raw_name]["unit"]),
                    )
                    for raw_name in ANALYTE_MAPPINGS
                    if data.get(float, raw_name) is not None
                ]
            ),
            viability=data.get(float, "Viability"),
            total_cell_density=data.get(float, "Total Density"),
            total_cell_density_unit=units.get(str, "Total Density"),
            viable_cell_density=data.get(float, "Viable Density"),
            viable_cell_density_unit=units.get(str, "Viable Density"),
            average_live_cell_diameter=data.get(float, "Average Live Cell Diameter"),
            total_cell_count=data.get(float, "Total Cell Count"),
            viable_cell_count=data.get(float, "Total Live Count"),
            osmolality=data.get(float, "Osm"),
            ph=data.get(float, "pH"),
            temperature=data.get(float, "Vessel Temperature (°C)"),
            po2=data.get(float, "PO2"),
            po2_unit=units.get(str, "PO2"),
            pco2=data.get(float, "PCO2"),
            pco2_unit=units.get(str, "PCO2"),
            carbon_dioxide_saturation=data.get(float, "CO2 Saturation"),
            oxygen_saturation=data.get(float, "O2 Saturation"),
            cell_type_processing_method=data.get(str, "Cell Type")
            if cell_density_dilution
            else None,
            cell_density_dilution_factor=try_float_or_none(str(cell_density_dilution)),
        )


@dataclass(frozen=True)
class SampleList:
    analyst: str
    samples: list[Sample]

    @staticmethod
    def get_analyst(sample: SeriesData) -> str:
        if analyst := sample.get(str, "Operator"):
            return analyst
        msg = "Unable to find the Operator."
        raise AllotropeConversionError(msg)

    @staticmethod
    def create(units: SeriesData, sample_data: list[SeriesData]) -> SampleList:
        return SampleList(
            analyst=SampleList.get_analyst(sample_data[0]),
            samples=[Sample.create(units, data) for data in sample_data],
        )


@dataclass(frozen=True)
class SampleData:
    sample_list: SampleList

    @staticmethod
    def parse_units(units: SeriesData) -> SeriesData:
        data: dict[str, str | None] = {}
        for key, value in units.series.items():
            if value is None:
                data[str(key)] = None
                continue

            value_str = str(value).strip()
            data[str(key)] = (
                None if value_str in ("-", "NaT") else value_str.replace(" ", "")
            )

        return SeriesData(pd.Series(data))

    @staticmethod
    def parse_data(
        raw_data: pd.DataFrame,
    ) -> tuple[SeriesData, list[SeriesData]]:
        sample_data = [SeriesData(row) for _, row in raw_data.iterrows()]

        if len(sample_data) == 0:
            msg = "Unable to find any sample."
            raise AllotropeConversionError(msg)

        if len(sample_data) == 1:
            return SeriesData(), sample_data

        first_row = sample_data[0]
        date_time_regex = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        if re.match(date_time_regex, first_row[str, "Date & Time"]) is None:
            return SampleData.parse_units(first_row), sample_data[1:]

        return SeriesData(), sample_data

    @staticmethod
    def create(raw_data: pd.DataFrame) -> SampleData:
        return SampleData(
            sample_list=SampleList.create(*SampleData.parse_data(raw_data)),
        )


def _create_measurement(sample: Sample, **kwargs: Any) -> Measurement:
    return Measurement(
        identifier=random_uuid_str(),
        measurement_time=sample.measurement_time,
        sample_identifier=sample.identifier,
        description=sample.sample_type,
        batch_identifier=sample.batch_identifier,
        **kwargs,
    )


def _get_measurements(sample: Sample) -> list[Measurement]:
    measurements = []

    # NOTE: only specifying this order to keep test results identical for refactor. Will remove in follow
    # up change that moves this logic into schema mapper.
    for detection_type in [
        "metabolite-detection",
        "cell-counting",
        "blood-gas-detection",
        "osmolality-detection",
        "ph-detection",
    ]:
        kwargs = {
            key: getattr(sample, key)
            for key in DETECTION_PROPERTY_MAPPING[detection_type]
        }
        data_processing = {
            key: value
            for key in DATA_PROCESSING_FIELDS
            if key in kwargs and (value := kwargs.pop(key)) is not None
        }
        if data_processing:
            kwargs["data_processing"] = DataProcessing(**data_processing)
        if any(value is not None for value in kwargs.values()):
            measurements.append(
                _create_measurement(
                    sample,
                    detection_type=detection_type,
                    **kwargs,
                )
            )

    return measurements


def create_metadata(title: Title, file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        unc_path=file_path,
        device_type=DEVICE_TYPE,
        model_number=MODEL_NUMBER,
        product_manufacturer=PRODUCT_MANUFACTURER,
        device_identifier=title.device_identifier,
        software_name=SOFTWARE_NAME,
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_identifier=NOT_APPLICABLE,
    )


def create_measurement_groups(
    title: Title, sample_list: SampleList
) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(
            analyst=sample_list.analyst,
            data_processing_time=title.processing_time,
            measurements=_get_measurements(sample),
        )
        for sample in sample_list.samples
    ]
