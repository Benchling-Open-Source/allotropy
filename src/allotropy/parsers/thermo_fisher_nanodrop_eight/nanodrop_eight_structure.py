from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    CalculatedDataItem,
    DataCube,
    DataCubeComponent,
    DataSource,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_nanodrop_eight import constants
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.pandas import map_rows, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none


@dataclass
class SpectroscopyRow:
    analyst: str | None
    timestamp: str
    experiment_type: str | None
    measurements: list[Measurement]
    calculated_data: list[CalculatedDataItem]

    @staticmethod
    def create(data: SeriesData) -> SpectroscopyRow:
        analyst = data.get(str, "user name")
        timestamp = data[str, "date & time"]
        experiment_type = data.get(str, "application")
        sample_id = data.get(str, "sample id", NOT_APPLICABLE, SeriesData.NOT_NAN)
        location_id = data.get(str, "location")

        is_na_experiment = experiment_type and "NA" in experiment_type

        a260_absorbance = data.get(float, "a260")
        a280_absorbance = data.get(float, "a280")
        measurements: list[Measurement] = []

        mass_concentration = get_first_not_none(
            lambda key: data.get(float, key.lower()),
            constants.CONCENTRATION_UNITS,
        )

        unit = get_first_not_none(
            lambda key: key if data.get(float, key.lower()) else None,
            constants.CONCENTRATION_UNITS,
        )

        spectra_data_cube = None
        wavelength_cols = [col for col in data.series.index if try_float_or_none(col)]
        absorbance_vals = [data.get(float, col) for col in wavelength_cols]
        wavelengths_or_none = [try_float_or_none(col) for col in wavelength_cols]
        wavelengths = [w for w in wavelengths_or_none if w]

        if len(absorbance_vals) and len(absorbance_vals) == len(wavelengths):
            spectra_data_cube = DataCube(
                label="absorption spectrum",
                structure_dimensions=[
                    DataCubeComponent(FieldComponentDatatype.double, "wavelength", "nm")
                ],
                structure_measures=[
                    DataCubeComponent(
                        FieldComponentDatatype.double, "absorbance", "mAU"
                    ),
                ],
                dimensions=[wavelengths],
                measures=[absorbance_vals],
            )

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
                    type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
                    identifier=random_uuid_str(),
                    data_cube=spectra_data_cube,
                    absorbance=absorbance,
                    detector_wavelength_setting=wavelength,
                    sample_identifier=sample_id,
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
        measurements.append(
            Measurement(
                type_=MeasurementType.ULTRAVIOLET_ABSORBANCE_SPECTRUM,
                identifier=random_uuid_str(),
                data_cube=spectra_data_cube,
                sample_identifier=sample_id,
                location_identifier=location_id,
            )
        )
        absorbance_ratios = {}
        for numerator, denominator in constants.ABSORBANCE_RATIOS:
            ratio = data.get(float, f"a{numerator}/a{denominator}")
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


def create_metadata(file_name: str, data: pd.DataFrame) -> Metadata:
    return Metadata(
        device_identifier=constants.DEVICE_IDENTIFIER,
        device_type=constants.DEVICE_TYPE,
        model_number=constants.MODEL_NUBMER,
        equipment_serial_number=data.iloc[0]["serial number"],
        file_name=file_name,
    )


def create_measurement_group(row: SpectroscopyRow) -> MeasurementGroup:
    return MeasurementGroup(
        measurement_time=row.timestamp,
        analyst=row.analyst,
        experiment_type=row.experiment_type,
        measurements=row.measurements,
    )
