from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_fisher_nanodrop_8000.nanodrop_8000_structure import (
    create_calculated_data,
    read_absorbances,
    read_mass_concentration_capture_wavelength,
)
from allotropy.parsers.thermo_fisher_nanodrop_eight import constants
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float, try_float_or_none


@dataclass
class SpectroscopyRow:
    timestamp: str
    experiment_type: str | None
    measurements: list[Measurement]
    calculated_data: list[CalculatedDocument]

    @staticmethod
    def create(data: SeriesData, header: SeriesData) -> SpectroscopyRow:
        absorbances = read_absorbances(data)
        experiment_type = header.get(str, "application")
        mass_concentration_capture_wavelength = (
            read_mass_concentration_capture_wavelength(
                data, experiment_type, absorbances
            )
        )
        mass_concentration = get_first_not_none(
            lambda key: data.get(float, key),
            ["conc.", "conc", "concentration"],
        )
        unit = get_first_not_none(
            lambda key: key if data.get(float, key.lower()) else None,
            constants.CONCENTRATION_UNITS,
        )

        spectra_data_cube = None
        float_cols = [col for col in data.series.index if try_float_or_none(col)]
        spectra_data = {try_float(col, col): data.get(float, col) for col in float_cols}
        if len(spectra_data) and None not in spectra_data.values():
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
                dimensions=[list(spectra_data.keys())],
                measures=[list(spectra_data.values())],
            )

        sample_id = data.get(
            str, ["sample id", "uid"], NOT_APPLICABLE, SeriesData.NOT_NAN
        )
        location_id = data.get(str, "location")
        measurements: list[Measurement] = []
        for wavelength, absorbance in absorbances.items():
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
                    if mass_concentration_capture_wavelength == wavelength
                    and mass_concentration
                    and unit
                    else None,
                )
            )
        if spectra_data_cube:
            measurements.append(
                Measurement(
                    type_=MeasurementType.ULTRAVIOLET_ABSORBANCE_SPECTRUM,
                    identifier=random_uuid_str(),
                    data_cube=spectra_data_cube,
                    sample_identifier=sample_id,
                    location_identifier=location_id,
                )
            )

        calculated_data = create_calculated_data(data, measurements)

        return SpectroscopyRow(
            data[str, ["date", "date & time"]],
            experiment_type,
            measurements,
            calculated_data,
        )


def create_metadata(data: SeriesData, file_path: str) -> Metadata:
    return Metadata(
        device_identifier=constants.DEVICE_IDENTIFIER,
        device_type=constants.DEVICE_TYPE,
        model_number=constants.MODEL_NUBMER,
        equipment_serial_number=data[str, "serial number"],
        file_name=Path(file_path).name,
        unc_path=file_path,
    )


def create_measurement_group(
    row: SpectroscopyRow, header: SeriesData
) -> MeasurementGroup:
    return MeasurementGroup(
        measurement_time=row.timestamp,
        analyst=header.get(str, "user name"),
        experiment_type=row.experiment_type,
        measurements=row.measurements,
    )
