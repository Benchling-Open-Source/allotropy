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
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str

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

        a260_absorbance = data.get(float, "a260")
        a280_absorbance = get_first_not_none(
            lambda key: data.get(float, key), ["a280", "a280 10mm"]
        )
        measurements: list[Measurement] = []

        mass_concentration = get_first_not_none(
            lambda key: data.get(float, key),
            ["conc.", "conc", "concentration"],
        )
        unit = data.get(str, "units")

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


def create_data(data: pd.DataFrame, file_name: str) -> Data:
    rows = SpectroscopyRow.create_rows(data)

    return Data(
        metadata=Metadata(
            device_identifier="Nanodrop",
            device_type="absorbance detector",
            model_number="Nanodrop Eight",
            file_name=file_name,
        ),
        measurement_groups=[
            MeasurementGroup(
                _measurement_time=row.timestamp,
                analyst=row.analyst,
                experiment_type=row.experiment_type,
                measurements=row.measurements,
            )
            for row in rows
        ],
        # NOTE: in current implementation, calculated data is reported at global level for some
        # reason
        # TODO(nstender): should we move this inside of measurements?
        calculated_data=[item for row in rows for item in row.calculated_data],
    )
