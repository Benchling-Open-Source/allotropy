from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    CalculatedDataItem,
    Data,
    DataSource,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    try_float_from_series_or_none,
    try_non_nan_str_from_series_or_none,
    try_str_from_series_or_none,
)

# These may be reported in the results, and are stored as calculated data
ABSORBANCE_RATIOS = [
    (260, 280),
    (260, 230),
]


@dataclass
class SpectroscopyRow:
    analyst: str | None
    timestamp: str
    experiment_type: str | None
    measurements: list[Measurement]
    absorbance_ratios: dict[tuple[int, int], float]

    @staticmethod
    def create(data: pd.Series[str]) -> SpectroscopyRow:
        analyst = try_str_from_series_or_none(data, "user id")
        timestamp = f'{try_str_from_series_or_none(data, "date")} {try_str_from_series_or_none(data, "time")}'
        experiment_type = try_str_from_series_or_none(data, "na type")

        sample_id = (
            try_non_nan_str_from_series_or_none(data, "sample id") or NOT_APPLICABLE
        )
        well_plate_id = try_non_nan_str_from_series_or_none(data, "plate id")
        location_id = try_str_from_series_or_none(data, "well")

        is_na_experiment = experiment_type and "NA" in experiment_type

        a260_absorbance = try_float_from_series_or_none(data, "a260")
        a280_absorbance = get_first_not_none(
            lambda key: try_float_from_series_or_none(data, key), ["a280", "a280 10mm"]
        )
        measurements = []

        mass_concentration = get_first_not_none(
            lambda key: try_float_from_series_or_none(data, key),
            ["conc.", "conc", "concentration"],
        )
        unit = try_str_from_series_or_none(data, "units")

        # We only capture mass concentration on one measurement document
        # TODO(nstender): why not just capture in both? Seems relevant, and would make this so much simpler.
        # capture concentration on the 260 measurement document if:
        #   - there is no experiment type and no 280 column add the concentration here
        # capture concentration on the 280 measurement document if:
        #   - the experiment type is something other than DNA or RNA
        #   - if the experiment type is not specified
        absorbances = (
            (
                260,
                a260_absorbance,
                is_na_experiment
                or not (experiment_type or a280_absorbance is not None),
            ),
            (280, a280_absorbance, not (experiment_type and is_na_experiment)),
        )

        for wavelength, absorbance, capture_concentration in absorbances:
            if not absorbance:
                continue
            measurements.append(
                Measurement(
                    identifier=random_uuid_str(),
                    absorbance=absorbance,
                    detector_wavelength_setting=wavelength,
                    sample_identifier=sample_id,
                    well_plate_identifier=well_plate_id,
                    location_identifier=location_id,
                    processed_data=ProcessedData(
                        features=[
                            ProcessedDataFeature(
                                result=mass_concentration,
                                unit=unit,
                            )
                        ],
                    )
                    if capture_concentration and mass_concentration and unit
                    else None,
                )
            )

        absorbance_ratios = {}
        for numerator, denominator in ABSORBANCE_RATIOS:
            ratio = try_float_from_series_or_none(data, f"{numerator}/{denominator}")
            if ratio:
                absorbance_ratios[(numerator, denominator)] = ratio

        return SpectroscopyRow(
            analyst,
            timestamp,
            experiment_type,
            measurements,
            absorbance_ratios,
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[SpectroscopyRow]:
        data.columns = data.columns.str.lower()
        return list(data.apply(SpectroscopyRow.create, axis="columns"))  # type: ignore[call-overload]


def _create_metadata(file_name: str) -> Metadata:
    return Metadata(
        device_identifier="Nanodrop",
        device_type="absorbance detector",
        model_number="Nanodrop Eight",
        file_name=file_name,
    )


def _create_measurement_groups(rows: list[SpectroscopyRow]) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(
            _measurement_time=row.timestamp,
            analyst=row.analyst,
            experiment_type=row.experiment_type,
            measurements=row.measurements,
        )
        for row in rows
    ]


def _create_calculated_data(rows: list[SpectroscopyRow]) -> list[CalculatedDataItem]:
    return [
        CalculatedDataItem(
            identifier=random_uuid_str(),
            name=f"A{numerator}/{denominator}",
            value=ratio,
            unit=UNITLESS,
            data_sources=[
                DataSource(identifier=measurement.identifier, feature="absorbance")
                for measurement in row.measurements
                if measurement.detector_wavelength_setting in (numerator, denominator)
            ],
        )
        for row in rows
        for (numerator, denominator), ratio in row.absorbance_ratios.items()
    ]


def create_data(data: pd.DataFrame, file_name: str) -> Data:
    rows = SpectroscopyRow.create_rows(data)

    return Data(
        metadata=_create_metadata(file_name),
        measurement_groups=_create_measurement_groups(rows),
        calculated_data=_create_calculated_data(rows),
    )
