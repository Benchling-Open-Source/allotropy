from __future__ import annotations

from pathlib import Path

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    ErrorDocument,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedDataDocument,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NEGATIVE_ZERO, NOT_APPLICABLE
from allotropy.parsers.unchained_labs_lunatic.constants import (
    CALCULATED_DATA_LOOKUP,
    DETECTION_TYPE,
    DEVICE_TYPE,
    INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG,
    MODEL_NUMBER,
    NO_DATE_OR_TIME_ERROR_MSG,
    NO_DEVICE_IDENTIFIER_ERROR_MSG,
    NO_MEASUREMENT_IN_PLATE_ERROR_MSG,
    NO_WAVELENGTH_COLUMN_ERROR_MSG,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
    WAVELENGTH_COLUMNS_RE,
)
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_calcdocs import (
    create_calculated_data,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.pandas import (
    map_rows,
    SeriesData,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
)


def _create_measurement(
    well_plate_data: SeriesData,
    header: SeriesData,
    wavelength_column: str,
) -> Measurement:
    if wavelength_column not in well_plate_data.series:
        msg = NO_MEASUREMENT_IN_PLATE_ERROR_MSG.format(wavelength_column)
        raise AllotropeConversionError(msg)

    wavelength_match = WAVELENGTH_COLUMNS_RE.match(wavelength_column)
    if not wavelength_match:
        raise AllotropeConversionError(INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG)
    if len(wavelength_match.groups()) > 1:
        wavelength, path_length = wavelength_match.groups()
    else:
        wavelength = wavelength_match.groups()[0]
        path_length = None

    background_wavelength = well_plate_data.get(float, "background wvl. (nm)")
    background_absorbance = None
    if background_wavelength is not None:
        background_absorbance = well_plate_data.get(
            float, f"background (a{int(background_wavelength)})"
        )

    measurement_identifier = random_uuid_str()

    error_documents = _get_error_documents(well_plate_data, wavelength_column)
    absorbance = well_plate_data.get(float, wavelength_column)

    if absorbance is None:
        error_documents.append(
            ErrorDocument(
                error=NOT_APPLICABLE,
                error_feature=DETECTION_TYPE.lower(),
            )
        )
    concentration_factor = well_plate_data.get(float, "concentration factor (ng/ul)")
    return Measurement(
        type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
        device_type=DEVICE_TYPE,
        detection_type=DETECTION_TYPE,
        identifier=measurement_identifier,
        detector_wavelength_setting=float(wavelength),
        electronic_absorbance_reference_wavelength_setting=background_wavelength,
        absorbance=absorbance if absorbance is not None else NEGATIVE_ZERO,
        sample_identifier=well_plate_data[str, "sample name"],
        location_identifier=well_plate_data[str, "plate position"],
        well_plate_identifier=well_plate_data.get(str, "plate id"),
        batch_identifier=well_plate_data.get(str, "sample group"),
        firmware_version=header.get(str, "client version"),
        sample_custom_info={
            "path length": float(path_length) if path_length is not None else None,
            "plate type": header.get(str, "plate type")
            or well_plate_data.get(str, "plate type"),
            "nr of plates": header.get(str, "nr of plates"),
            "blanks": header.get(str, "blanks"),
            "plate description": header.get(str, "nan"),
            "molar attenuation coefficient setting": well_plate_data.get(float, "e1%"),
        },
        device_control_custom_info={
            "path length mode": well_plate_data.get(str, "path length mode"),
            "pump": well_plate_data.get(str, "pump"),
            "column": header.get(str, "column") or well_plate_data.get(str, "column"),
        },
        measurement_custom_info={
            "electronic_absorbance_reference_absorbance": background_absorbance,
            **well_plate_data.get_unread(
                # Skip already mapped columns from well plate data (repeated in CSV no header cases)
                skip={
                    "time",
                    "row",
                    "concentration factor (ng/ul)",
                    "application",
                    "concentration (ng/ul)",
                    "background wvl. (nm)",
                    "plate id",
                    "plate position",
                    "plate type",
                    "instrument id",
                    "column",
                    # Strings to skip since these are already captured as measurements/calculated data
                    # Skip absorbance measurements with a### (10mm) -- spectral scans
                    r"^a\d{3} \(10mm\)$",
                    # a###/a### -- calculated purity values
                    r"^a\d{3}/a\d{3}$",
                    # a### -- raw absorbance measurement
                    r"^a\d{3}$",
                },
            ),
        },
        error_document=error_documents,
        processed_data_document=ProcessedDataDocument(
            identifier=random_uuid_str(), concentration_factor=concentration_factor
        )
        if concentration_factor is not None
        else None,
        wavelength_identifier=wavelength_column,
        calc_docs_custom_info={
            item["column"]: well_plate_data.get(float, item["column"])
            for item in CALCULATED_DATA_LOOKUP.get(wavelength_column, [])
        },
    )


def _get_error_documents(
    well_plate_data: SeriesData,
    wavelength_column: str,
) -> list[ErrorDocument]:
    error_documents = []
    for item in CALCULATED_DATA_LOOKUP.get(wavelength_column, []):
        value = well_plate_data.get(float, item["column"])
        if value is None:
            error_documents.append(
                ErrorDocument(
                    error=NOT_APPLICABLE,
                    error_feature=item["name"],
                )
            )
    return error_documents


def _create_measurement_group(
    data: SeriesData,
    wavelength_columns: list[str],
    header: SeriesData,
) -> MeasurementGroup:
    timestamp = header.get(str, "date")
    # Support timestamp from metadata section, but overide with columns in data if specified.
    date = data.get(str, "date")
    time = data.get(str, "time")
    if date and time:
        timestamp = f"{date} {time}"

    return MeasurementGroup(
        measurement_time=assert_not_none(timestamp, msg=NO_DATE_OR_TIME_ERROR_MSG),
        analyst=header.get(str, "test performed by"),
        analytical_method_identifier=data.get(str, "application")
        or header.get(str, "application"),
        experimental_data_identifier=header.get(str, "experiment name"),
        plate_well_count=96,
        measurements=[
            _create_measurement(data, header, wavelength_column)
            for wavelength_column in wavelength_columns
        ],
    )


def create_metadata(header: SeriesData, file_path: str) -> Metadata:
    asm_file_identifier = Path(file_path).with_suffix(".json")
    device_identifier = header.get(str, "instrument id") or header.get(
        str, "instrument"
    )
    return Metadata(
        model_number=MODEL_NUMBER,
        product_manufacturer=PRODUCT_MANUFACTURER,
        device_identifier=assert_not_none(
            device_identifier, msg=NO_DEVICE_IDENTIFIER_ERROR_MSG
        ),
        software_name=SOFTWARE_NAME,
        software_version=header.get(str, "software version"),
        file_name=Path(file_path).name,
        unc_path=file_path,
        asm_file_identifier=asm_file_identifier.name,
        data_system_instance_id=NOT_APPLICABLE,
        custom_info_doc=header.get_unread(
            # Skip already mapped columns from well plate data (repeated in CSV no header cases)
            skip={
                "time",
                "row",
                "path length mode",
                "sample group",
                "pump",
                "concentration factor (ng/ul)",
                "sample name",
                "application",
                "concentration (ng/ul)",
                "background wvl. (nm)",
                "plate id",
                "plate position",
                # Strings to skip since these are already captured as measurements/calculated data
                # Skip absorbance spectrum measurements with a### (10mm)
                r"^a\d{3} \(10mm\)$",
                # a###/a###
                r"^a\d{3}/a\d{3}$",
                # a###
                r"^a\d{3}$",
                # background a###
                r"^background \(a\d{3}\)$",
                # a### concentration (ng/uL)
                r"^a\d{3} concentration \(ng/ul\)$",
            },
        ),
    )


def create_measurement_groups(
    header: SeriesData, data: pd.DataFrame
) -> tuple[list[MeasurementGroup], list[CalculatedDocument]]:
    wavelength_columns = list(filter(WAVELENGTH_COLUMNS_RE.match, data.columns))
    if not wavelength_columns:
        raise AllotropeConversionError(NO_WAVELENGTH_COLUMN_ERROR_MSG)

    def make_group(data: SeriesData) -> MeasurementGroup:
        return _create_measurement_group(data, wavelength_columns, header)

    measurement_groups = map_rows(data, make_group)
    return measurement_groups, create_calculated_data(measurement_groups)
