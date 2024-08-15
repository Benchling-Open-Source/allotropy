from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import numpy as np
import pandas as pd

from allotropy.allotrope.schema_mappers.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    Analyte,
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.novabio_flex2.constants import (
    ANALYTE_MAPPINGS,
    BLOOD_GAS_DETECTION_MAPPINGS,
    CELL_COUNTER_MAPPINGS,
    DEVICE_TYPE,
    FILENAME_REGEX,
    INVALID_FILENAME_MESSAGE,
    MODEL_NUMBER,
    OSMOLALITY_DETECTION_MAPPINGS,
    PH_DETECTION_MAPPINGS,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
)
from allotropy.parsers.utils.pandas import read_csv, SeriesData
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
    cell_counter_properties: dict[str, Any]
    blood_gas_properties: dict[str, Any]
    osmolality_properties: dict[str, Any]
    ph_properties: dict[str, Any]
    cell_type_processing_method: str | None
    cell_density_dilution_factor: float | None

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
            cell_counter_properties=cls._get_properties(data, CELL_COUNTER_MAPPINGS),
            blood_gas_properties=cls._get_properties(
                data, BLOOD_GAS_DETECTION_MAPPINGS
            ),
            osmolality_properties=cls._get_properties(
                data, OSMOLALITY_DETECTION_MAPPINGS
            ),
            ph_properties=cls._get_properties(data, PH_DETECTION_MAPPINGS),
            cell_type_processing_method=data.get(str, "Cell Type"),
            cell_density_dilution_factor=try_float_or_none(str(cell_density_dilution)),
        )

    @classmethod
    def _get_properties(
        cls, data: SeriesData, property_mappings: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            property_name: data.get(float, column_name)
            for property_name, column_name in property_mappings.items()
            if data.get(float, column_name) is not None
        }


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
    if sample.analytes:
        measurements.append(
            _create_measurement(
                sample,
                detection_type="metabolite-detection",
                analytes=sample.analytes,
            )
        )

    if sample.cell_counter_properties:
        measurements.append(
            _create_measurement(
                sample,
                detection_type="cell-counting",
                cell_type_processing_method=sample.cell_type_processing_method,
                cell_density_dilution_factor=sample.cell_density_dilution_factor,
                **sample.cell_counter_properties,
            )
        )

    if sample.blood_gas_properties:
        measurements.append(
            _create_measurement(
                sample,
                detection_type="blood-gas-detection",
                **sample.blood_gas_properties,
            )
        )

    if sample.osmolality_properties:
        measurements.append(
            _create_measurement(
                sample,
                detection_type="osmolality-detection",
                **sample.osmolality_properties,
            )
        )

    if sample.ph_properties:
        measurements.append(
            _create_measurement(
                sample,
                detection_type="ph-detection",
                **sample.ph_properties,
            )
        )

    return measurements


def create_data(named_file_contents: NamedFileContents) -> Data:
    # NOTE: calling parse_dates and removing NaN clears empty rows.
    data = read_csv(named_file_contents.contents, parse_dates=["Date & Time"]).replace(
        np.nan, None
    )
    title = Title.create(named_file_contents.original_file_name)
    sample_list = SampleList.create(data)

    return Data(
        Metadata(
            file_name=named_file_contents.original_file_name,
            device_type=DEVICE_TYPE,
            model_number=MODEL_NUMBER,
            product_manufacturer=PRODUCT_MANUFACTURER,
            device_identifier=title.device_identifier,
            software_name=SOFTWARE_NAME,
        ),
        measurement_groups=[
            MeasurementGroup(
                analyst=sample_list.analyst,
                data_processing_time=title.processing_time,
                measurements=_get_measurements(sample),
            )
            for sample in sample_list.samples
        ],
    )
