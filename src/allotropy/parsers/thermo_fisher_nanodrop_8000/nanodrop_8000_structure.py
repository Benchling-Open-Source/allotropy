from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    CalculatedDataItem,
    DataSource,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_nanodrop_8000 import constants
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass
class SpectroscopyRow:
    analyst: str | None
    timestamp: str
    experiment_type: str | None
    measurements: list[Measurement]
    calculated_data: list[CalculatedDataItem]

    @staticmethod
    def create(data: SeriesData) -> SpectroscopyRow:
        analyst = data.get(str, "user id")
        timestamp = f'{data[str, "date"]} {data.get(str, "time")}'
        experiment_type = data.get(str, "na type")

        sample_id = data.get(str, "sample id", NOT_APPLICABLE, SeriesData.NOT_NAN)
        well_plate_id = data.get(str, "plate id", validate=SeriesData.NOT_NAN)
        location_id = data[str, "well"]

        is_na_experiment = experiment_type and "NA" in experiment_type

        # TODO(nstender): the fact that there are more than two wavelength columns seems to indicate
        # that there may be more options than 260 and 280, figure out how to handle other
        # possible wavelengths.
        absorbances_by_wavelength: dict[float | None, float | None] = {}
        # NOTE: this range is just a reasonable sanity check so we don't have to use a "while True"
        for i in range(1, len(data.series.index) + 1):
            if not data.has_key(f"abs {i}"):
                break
            absorbances_by_wavelength[data.get(float, f"nm {i}")] = data.get(
                float, f"abs {i}"
            )

        a260_absorbance = data.get(float, "a260") or absorbances_by_wavelength.get(260)
        a280_absorbance = get_first_not_none(
            lambda key: data.get(float, key), ["a280", "a280 10mm"]
        ) or absorbances_by_wavelength.get(280)

        measurements: list[Measurement] = []

        mass_concentration = get_first_not_none(
            lambda key: data.get(float, key),
            ["conc.", "conc", "concentration"],
        )
        unit = data.get(str, "units")

        # NOTE: mass concentration is captured by a different wavelength depending on the experiment type.
        # DNA and RNA are captured as 260nm, while other experiment types are typically 280nm.
        # Given this, we apply the following logic:
        #
        # capture concentration on the 260 measurement document if:
        #   - there is no experiment type and no 280 column
        # capture concentration on the 280 measurement document if:
        #   - the experiment type is something other than DNA or RNA
        #   - the experiment type is not specified
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
            if absorbance is None:
                continue
            measurements.append(
                Measurement(
                    type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
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
        for numerator, denominator in constants.ABSORBANCE_RATIOS:
            ratio = data.get(float, f"{numerator}/{denominator}")
            if ratio:
                absorbance_ratios[(numerator, denominator)] = ratio

        calculated_data = [
            CalculatedDataItem(
                identifier=random_uuid_str(),
                name=f"A{numerator}/{denominator}",
                value=ratio,
                unit=UNITLESS,
                data_sources=[
                    DataSource(identifier=measurement.identifier, feature="absorbance")
                    for measurement in measurements
                    if measurement.detector_wavelength_setting
                    in (numerator, denominator)
                ],
            )
            for (numerator, denominator), ratio in absorbance_ratios.items()
        ]

        return SpectroscopyRow(
            analyst,
            timestamp,
            experiment_type,
            measurements,
            calculated_data,
        )

    @staticmethod
    def create_rows(data: pd.DataFrame) -> list[SpectroscopyRow]:
        data.columns = data.columns.str.lower()
        return map_rows(data, SpectroscopyRow.create)


def create_metadata(file_name: str) -> Metadata:
    return Metadata(
        device_identifier=constants.DEVICE_IDENTIFIER,
        device_type=constants.DEVICE_TYPE,
        model_number=constants.MODEL_NUBMER,
        file_name=file_name,
    )


def create_measurement_group(row: SpectroscopyRow) -> MeasurementGroup:
    return MeasurementGroup(
        measurement_time=row.timestamp,
        analyst=row.analyst,
        experiment_type=row.experiment_type,
        measurements=row.measurements,
    )
