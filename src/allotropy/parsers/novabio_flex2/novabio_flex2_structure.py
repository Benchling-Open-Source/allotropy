from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Analyte,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.novabio_flex2.constants import (
    ANALYTE_MAPPINGS,
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
    def create(filename: str) -> Title:
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
    pco2: float | None = None
    carbon_dioxide_saturation: float | None = None
    oxygen_saturation: float | None = None
    ph: float | None = None
    temperature: float | None = None
    osmolality: float | None = None
    viability: float | None = None
    total_cell_density: float | None = None
    viable_cell_density: float | None = None
    average_live_cell_diameter: float | None = None
    total_cell_count: float | None = None
    viable_cell_count: float | None = None
    cell_type_processing_method: str | None = None
    cell_density_dilution_factor: float | None = None

    @classmethod
    def create(cls, series: pd.Series[Any]) -> Sample:
        data = SeriesData(series)
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
                        ANALYTE_MAPPINGS[raw_name]["unit"],
                    )
                    for raw_name in ANALYTE_MAPPINGS
                    if data.get(float, raw_name) is not None
                ]
            ),
            viability=data.get(float, "Viability"),
            total_cell_density=data.get(float, "Total Density"),
            viable_cell_density=data.get(float, "Viable Density"),
            average_live_cell_diameter=data.get(float, "Average Live Cell Diameter"),
            total_cell_count=data.get(float, "Total Cell Count"),
            viable_cell_count=data.get(float, "Total Live Count"),
            osmolality=data.get(float, "Osm"),
            ph=data.get(float, "pH"),
            temperature=data.get(float, "Vessel Temperature (°C)"),
            po2=data.get(float, "PO2"),
            pco2=data.get(float, "PCO2"),
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
    def create(data: pd.DataFrame) -> SampleList:
        sample_data_rows = [row for _, row in data.iterrows()]

        if not sample_data_rows:
            msg = "Unable to find any sample."
            raise AllotropeConversionError(msg)

        analyst = sample_data_rows[0].get("Operator")

        if analyst is None:
            msg = "Unable to find the Operator."
            raise AllotropeConversionError(msg)

        return SampleList(
            analyst=str(analyst),
            samples=[Sample.create(sample_data) for sample_data in sample_data_rows],
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
        if any(value is not None for value in kwargs.values()):
            measurements.append(
                _create_measurement(
                    sample,
                    detection_type=detection_type,
                    **kwargs,
                )
            )

    return measurements


def create_metadata(title: Title, file_name: str) -> Metadata:
    return Metadata(
        file_name=file_name,
        device_type=DEVICE_TYPE,
        model_number=MODEL_NUMBER,
        product_manufacturer=PRODUCT_MANUFACTURER,
        device_identifier=title.device_identifier,
        software_name=SOFTWARE_NAME,
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
