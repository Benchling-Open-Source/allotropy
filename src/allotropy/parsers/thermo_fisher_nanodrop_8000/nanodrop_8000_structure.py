from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_nanodrop_8000 import constants
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def read_absorbances(data: SeriesData) -> dict[float, float]:
    # Read absorbances from abs <idx>, nm <idx> pair columns.
    absorbances: dict[float, float] = {}
    # NOTE: this range is just a reasonable sanity check so we don't have to use a "while True"
    for i in range(1, len(data.series.index) + 1):
        if not data.has_key(f"nm {i}"):
            break
        wavelength = data.get(float, f"nm {i}", validate=SeriesData.NOT_NAN)
        absorbance = data.get(float, f"abs {i}", validate=SeriesData.NOT_NAN)
        if wavelength is None or absorbance is None:
            continue
        absorbances[wavelength] = absorbance

    # Read absorbance columns with format "a<wavelength> <suffix>?", handle these as they come up.
    if (a230_absorbance := data.get(float, "a230")) is not None:
        absorbances[230] = a230_absorbance
    if (a260_absorbance := data.get(float, "a260")) is not None:
        absorbances[260] = a260_absorbance
    if (a280_absorbance := data.get(float, ["a280", "a280 10mm"])) is not None:
        absorbances[280] = a280_absorbance

    return absorbances


def read_mass_concentration_capture_wavelength(
    data: SeriesData, experiment_type: str | None, absorbances: dict[float, float]
) -> float:
    # NOTE: mass concentration is captured by a different wavelength depending on the experiment type.
    # DNA and RNA are captured as 260nm, while other experiment types are typically 280nm.
    # Given this, we apply the following logic:
    #
    # capture concentration on the 260 measurement document if:
    #   - there is no experiment type and no 280 column
    # capture concentration on the 280 measurement document if:
    #   - the experiment type is something other than DNA or RNA
    #   - the experiment type is not specified
    mass_concentration_capture_wavelength = data.get(float, "cursor nm")
    if mass_concentration_capture_wavelength is None:
        is_na_experiment = experiment_type and "NA" in experiment_type
        if not is_na_experiment and absorbances.get(280) is not None:
            mass_concentration_capture_wavelength = 280
        else:
            mass_concentration_capture_wavelength = 260

    return mass_concentration_capture_wavelength


def create_calculated_data(
    data: SeriesData, measurements: list[Measurement]
) -> list[CalculatedDocument]:
    # Read absorbance ratios from pre-calculated columns.
    absorbance_ratios = {}
    for numerator, denominator in constants.ABSORBANCE_RATIOS:
        ratio = data.get(
            float, [f"{numerator}/{denominator}", f"a{numerator}/a{denominator}"]
        )
        if ratio:
            absorbance_ratios[(numerator, denominator)] = ratio

    # Create a mapping of wavelengths to measurement IDs
    wavelength_to_measurement = {}
    for measurement in measurements:
        if measurement.detector_wavelength_setting is not None:
            wavelength_key = str(measurement.detector_wavelength_setting)
            wavelength_to_measurement[wavelength_key] = Referenceable(
                uuid=measurement.identifier
            )

    calculated_data = [
        CalculatedDocument(
            uuid=random_uuid_str(),
            name=f"A{numerator}/{denominator}",
            value=ratio,
            unit=UNITLESS,
            data_sources=[
                DataSource(
                    feature="absorbance",
                    reference=wavelength_to_measurement[str(wavelength)],
                )
                for wavelength in (numerator, denominator)
                if str(wavelength) in wavelength_to_measurement
            ],
        )
        for (numerator, denominator), ratio in absorbance_ratios.items()
    ]

    # Read all formulas <idx> columns into calculated data.
    # NOTE: this range is just a reasonable sanity check so we don't have to use a "while True"
    for i in range(1, len(data.series.index) + 1):
        if not data.has_key(f"formula {i}") and data.has_key(f"formula name {i}"):
            break
        if (
            value := data.get(float, f"formula value {i}", validate=SeriesData.NOT_NAN)
        ) is None:
            continue

        formula_wavelengths = []
        formula_str = data[str, f"formula {i}"]
        for wavelength_key, measurement_ref in wavelength_to_measurement.items():
            # Check if the measurement wavelength is in the formula, remove ".0" from int floats
            if wavelength_key.replace(".0", "") in formula_str:
                formula_wavelengths.append((wavelength_key, measurement_ref))

        calculated_data.append(
            CalculatedDocument(
                uuid=random_uuid_str(),
                name=data[str, f"formula name {i}"],
                value=value,
                unit=UNITLESS,
                data_sources=[
                    DataSource(feature="absorbance", reference=measurement_ref)
                    for _, measurement_ref in formula_wavelengths
                ],
            )
        )

    return calculated_data


@dataclass
class SpectroscopyRow:
    analyst: str | None
    timestamp: str
    experiment_type: str | None
    measurements: list[Measurement]
    calculated_data: list[CalculatedDocument]

    @staticmethod
    def create(data: SeriesData) -> SpectroscopyRow:
        absorbances = read_absorbances(data)
        experiment_type = data.get(str, "na type")
        mass_concentration_capture_wavelength = (
            read_mass_concentration_capture_wavelength(
                data, experiment_type, absorbances
            )
        )
        mass_concentration = get_first_not_none(
            lambda key: data.get(float, key),
            ["conc.", "conc", "concentration"],
        )
        unit = data.get(str, "units")

        measurements: list[Measurement] = []
        for wavelength, absorbance in absorbances.items():
            if absorbance is None:
                continue
            measurements.append(
                Measurement(
                    type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
                    identifier=random_uuid_str(),
                    absorbance=absorbance,
                    detector_wavelength_setting=wavelength,
                    sample_identifier=data.get(
                        str, "sample id", NOT_APPLICABLE, SeriesData.NOT_NAN
                    ),
                    well_plate_identifier=data.get(
                        str, "plate id", validate=SeriesData.NOT_NAN
                    ),
                    location_identifier=data[str, "well"],
                    processed_data=ProcessedData(
                        features=[
                            ProcessedDataFeature(
                                result=mass_concentration,
                                unit=unit,
                            )
                        ],
                    )
                    if mass_concentration_capture_wavelength == wavelength
                    and mass_concentration
                    and unit
                    else None,
                )
            )

        calculated_data = create_calculated_data(data, measurements)

        return SpectroscopyRow(
            data.get(str, "user id"),
            f'{data[str, "date"]} {data.get(str, "time")}',
            experiment_type,
            measurements,
            calculated_data,
        )


def create_metadata(file_path: str) -> Metadata:
    return Metadata(
        device_identifier=constants.DEVICE_IDENTIFIER,
        device_type=constants.DEVICE_TYPE,
        model_number=constants.MODEL_NUBMER,
        file_name=Path(file_path).name,
        unc_path=file_path,
    )


def create_measurement_group(row: SpectroscopyRow) -> MeasurementGroup:
    return MeasurementGroup(
        measurement_time=row.timestamp,
        analyst=row.analyst,
        experiment_type=row.experiment_type,
        measurements=row.measurements,
    )
