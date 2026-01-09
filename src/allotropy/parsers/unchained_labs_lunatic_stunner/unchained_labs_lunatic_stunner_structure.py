from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import re
from typing import Any

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import (
    MilliAbsorbanceUnit,
    Nanometer,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    ErrorDocument,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedDataDocument,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NEGATIVE_ZERO, NOT_APPLICABLE
from allotropy.parsers.unchained_labs_lunatic_stunner.constants import (
    CALCULATED_DATA_LOOKUP,
    DEFAULT_DETECTION_TYPE,
    DEVICE_TYPE,
    DYNAMIC_LIGHT_SCATTERING_DETECTION_TYPE,
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
from allotropy.parsers.unchained_labs_lunatic_stunner.unchained_labs_lunatic_stunner_calcdocs import (
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


def _extract_peak_data(well_plate_data: SeriesData) -> list[dict[str, Any]]:
    """Extract peak data from well plate data and return as list of peak info dictionaries."""
    peak_data = []

    peak_pattern = re.compile(r"peak (\d+) ")
    peak_numbers = set()

    for column in well_plate_data.series.index:
        match = peak_pattern.match(str(column).lower())
        if match:
            peak_numbers.add(int(match.group(1)))

    for peak_num in sorted(peak_numbers):
        peak_info: dict[str, Any] = {}

        mean_dia = well_plate_data.get(float, f"peak {peak_num} mean dia (nm)")
        if mean_dia is not None:
            peak_info["peak mean diameter"] = mean_dia

        mode_dia = well_plate_data.get(float, f"peak {peak_num} mode dia (nm)")
        if mode_dia is not None:
            peak_info["peak mode diameter"] = mode_dia

        est_mw = well_plate_data.get(float, f"peak {peak_num} est. mw (kda)")
        if est_mw is not None:
            peak_info["peak est. MW"] = est_mw

        intensity = well_plate_data.get(float, f"peak {peak_num} intensity (%)")
        if intensity is not None:
            peak_info["peak intensity"] = intensity

        mass = well_plate_data.get(float, f"peak {peak_num} mass (%)")
        if mass is not None:
            peak_info["peak mass"] = mass

        peak_info["peak index"] = str(peak_num)

        if len(peak_info) > 1:
            peak_data.append(peak_info)

    return peak_data


def _get_calculated_value_and_is_na(
    series: SeriesData, key: str
) -> tuple[float | None, bool]:
    """Return value and whether the source cell is literal N/A.

    - If the raw cell value is the string literal "N/A", returns (NEGATIVE_ZERO, True).
    - If the cell is empty/NaN, returns (None, False) so caller can skip the key.
    - Otherwise, returns (float value, False).
    """
    raw_string = series.get(str, key, validate=SeriesData.NOT_NAN)
    if raw_string is None:
        return None, False
    stripped = str(raw_string).strip()
    if stripped == "":
        return None, False
    if stripped.upper() == NOT_APPLICABLE:
        return NEGATIVE_ZERO, True
    return series.get(float, key), False


def _is_literal_not_applicable(series: SeriesData, key: str) -> bool:
    """Return True if the source cell is the literal string N/A (case-insensitive)."""
    raw_string = series.get(str, key, validate=SeriesData.NOT_NAN)
    if raw_string is None:
        return False
    return str(raw_string).strip().upper() == NOT_APPLICABLE


def _create_measurement(
    well_plate_data: SeriesData,
    header: SeriesData,
    wavelength_columns: list[str],
) -> Measurement:
    absorbance_errors: list[ErrorDocument] = []
    for wavelength_column in wavelength_columns:
        if wavelength_column not in well_plate_data.series:
            msg = NO_MEASUREMENT_IN_PLATE_ERROR_MSG.format(wavelength_column)
            raise AllotropeConversionError(msg)

        wavelength_match = WAVELENGTH_COLUMNS_RE.match(wavelength_column)
        if not wavelength_match:
            raise AllotropeConversionError(INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG)

        absorbance_is_na = _is_literal_not_applicable(
            well_plate_data, wavelength_column
        )
        if absorbance_is_na:
            absorbance_errors.append(
                ErrorDocument(
                    error=NOT_APPLICABLE,
                    error_feature=f"{DEFAULT_DETECTION_TYPE.lower()}",
                )
            )

    background_wavelength = well_plate_data.get(float, "background wvl. (nm)")
    background_absorbance = None
    if background_wavelength is not None:
        background_absorbance = well_plate_data.get(
            float, f"background (a{int(background_wavelength)})"
        )

    measurement_identifier = random_uuid_str()
    peak_data = _extract_peak_data(well_plate_data)

    error_documents: list[ErrorDocument] = []

    concentration_factor = well_plate_data.get(float, "concentration factor (ng/ul)")
    application = header.get(str, "application")
    analytical_method_identifier = (
        well_plate_data.get(str, "application") or application
    )
    experimental_data_identifier = header.get(str, "experiment name")
    detection_type = DEFAULT_DETECTION_TYPE
    if application and "B22 & kD" in application:
        detection_type = DYNAMIC_LIGHT_SCATTERING_DETECTION_TYPE

    calculated_data_values, calculated_data_errors = _get_calculated_data_values(
        well_plate_data, wavelength_columns
    )

    error_documents.extend(calculated_data_errors)
    error_documents.extend(absorbance_errors)

    # Initialize optional variables to None; set if applicable
    spectrum_data_cube: DataCube | None = None
    absorbance_value: float | None = None
    detector_wavelength_setting: float | None = None
    wavelength_identifier: str | None = None

    if len(wavelength_columns) > 1:
        spectrum_data_cube = _get_spectrum_data_cube(
            well_plate_data, wavelength_columns
        )
    elif len(wavelength_columns) == 1:
        wavelength_match = WAVELENGTH_COLUMNS_RE.match(wavelength_columns[0])
        wavelength, _ = wavelength_match.groups() if wavelength_match else ("", "")
        absorbance_tmp = well_plate_data.get(float, wavelength_columns[0])
        absorbance_value = (
            absorbance_tmp if absorbance_tmp is not None else NEGATIVE_ZERO
        )
        detector_wavelength_setting = float(wavelength) if wavelength else None
        wavelength_identifier = wavelength_columns[0]

    return Measurement(
        type_=(
            MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_SPECTRUM
            if len(wavelength_columns) > 1
            else MeasurementType.ULTRAVIOLET_ABSORBANCE
        ),
        device_type=DEVICE_TYPE,
        detection_type=detection_type,
        identifier=measurement_identifier,
        analytical_method_identifier=analytical_method_identifier,
        experimental_data_identifier=experimental_data_identifier,
        detector_wavelength_setting=detector_wavelength_setting,
        electronic_absorbance_reference_wavelength_setting=background_wavelength,
        absorbance=absorbance_value,
        sample_identifier=well_plate_data[str, "sample name"],
        location_identifier=well_plate_data[str, "plate position"],
        well_plate_identifier=well_plate_data.get(str, "plate id"),
        batch_identifier=well_plate_data.get(str, "sample group"),
        firmware_version=header.get(str, "client version"),
        number_of_averages=well_plate_data.get(float, "number of acquisitions"),
        integration_time=well_plate_data.get(float, "acquisition time (s)"),
        compartment_temperature=well_plate_data.get(float, "temperature (°c)"),
        sample_custom_info={
            "plate type": header.get(str, "plate type")
            or well_plate_data.get(str, "plate type"),
            "nr of plates": header.get(str, "nr of plates"),
            "blanks": header.get(str, "blanks"),
            "plate description": header.get(str, "nan", duplicate_strategy="last"),
            "molar attenuation coefficient setting": well_plate_data.get(float, "e1%"),
            "analyte": well_plate_data.get(str, "analyte"),
            "buffer": well_plate_data.get(str, "buffer"),
            "molecular weight (kda)": well_plate_data.get(
                float, "molecular weight (kda)"
            ),
        },
        device_control_custom_info={
            "path length mode": well_plate_data.get(str, "path length mode"),
            "pump": well_plate_data.get(str, "pump"),
            "column": header.get(str, "column") or well_plate_data.get(str, "column"),
            "Number of acquisitions used": well_plate_data.get(
                str, "number of acquisitions used"
            ),
            "Acquisition filtering": well_plate_data.get(str, "acquisition filtering"),
        },
        error_document=error_documents,
        processed_data_document=(
            ProcessedDataDocument(
                identifier=random_uuid_str(),
                concentration_factor=concentration_factor,
                peak_list_custom_info=peak_data,
            )
            if concentration_factor is not None or peak_data
            else None
        ),
        calc_docs_custom_info={
            **calculated_data_values,
            **{
                "b22 linear fit": well_plate_data.get(str, "b22 linear fit"),
                "kd linear fit": well_plate_data.get(str, "kd linear fit"),
            },
        },
        measurement_custom_info={
            "electronic_absorbance_reference_absorbance": background_absorbance,
            **_filter_empty_string_values(
                well_plate_data.get_unread(
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
                )
            ),
        },
        spectrum_data_cube=spectrum_data_cube,
        wavelength_identifier=wavelength_identifier,
    )


def _get_spectrum_data_cube(
    well_plate_data: SeriesData, wavelength_columns: list[str]
) -> DataCube:
    wavelengths, absorbances = _get_wavelengths_and_absorbance(
        well_plate_data, wavelength_columns
    )

    return DataCube(
        label="absorbance-spectrum",
        structure_dimensions=[
            DataCubeComponent(
                concept="wavelength",
                type_=FieldComponentDatatype.double,
                unit=Nanometer.unit,
            )
        ],
        structure_measures=[
            DataCubeComponent(
                concept="absorbance",
                type_=FieldComponentDatatype.double,
                unit=MilliAbsorbanceUnit.unit,
            )
        ],
        dimensions=[wavelengths],
        measures=[absorbances],
    )


def _get_wavelengths_and_absorbance(
    well_plate_data: SeriesData, wavelength_columns: list[str]
) -> tuple[list[float], list[float]]:
    wavelength_to_absorbance: dict[float, Decimal | None] = {}
    for wavelength_column in wavelength_columns:
        match = WAVELENGTH_COLUMNS_RE.match(wavelength_column)
        if not match:
            raise AllotropeConversionError(INCORRECT_WAVELENGTH_COLUMN_FORMAT_ERROR_MSG)
        wavelength_str, _ = match.groups()
        wavelength = float(wavelength_str)
        # Read as string to preserve precision; fallback to float; allow None
        raw_str = well_plate_data.get(
            str, wavelength_column, validate=SeriesData.NOT_NAN
        )
        absorbance: Decimal | None
        if raw_str is None or str(raw_str).strip() == "":
            absorbance = None
        else:
            absorbance = Decimal(str(raw_str).strip())

        if wavelength in wavelength_to_absorbance:
            previous_absorbance = wavelength_to_absorbance[wavelength]
            if absorbance is None or previous_absorbance is None:
                continue
            else:
                wavelength_to_absorbance[
                    wavelength
                ] = _get_absorbance_with_highest_precision(
                    previous_absorbance, absorbance
                )

        else:
            wavelength_to_absorbance[wavelength] = absorbance

    sorted_wavelengths = sorted(wavelength_to_absorbance.keys())

    absorbances = []
    for w in sorted_wavelengths:
        absorbance = wavelength_to_absorbance[w]
        if absorbance is None:
            absorbances.append(float(NEGATIVE_ZERO))
        else:
            absorbances.append(float(absorbance))

    return sorted_wavelengths, absorbances


def _get_absorbance_with_highest_precision(
    absorbance1: Decimal, absorbance2: Decimal
) -> Decimal:
    def _int_exponent(d: Decimal) -> int:
        exp = d.as_tuple().exponent
        if not isinstance(exp, int):
            msg = "Invalid absorbance value (NaN/Inf) not allowed for precision comparison."
            raise AllotropeConversionError(msg)
        return exp

    exp1 = _int_exponent(absorbance1)
    exp2 = _int_exponent(absorbance2)

    # Determine which has higher precision (more decimal places => smaller exponent),
    # for example, 1.56 has an exponent of -2, while 1.562 has an exponent of -3.
    if exp1 < exp2:
        high_precision = absorbance1
        low_precision, low_precision_exp = absorbance2, exp2
    else:
        high_precision = absorbance2
        low_precision, low_precision_exp = absorbance1, exp1

    # Round both to the lower precision and ensure they match
    quant = Decimal(1).scaleb(low_precision_exp)  # e.g., 1E-2 for two decimal places
    if high_precision.quantize(quant) != low_precision.quantize(quant):
        msg = (
            f"Conflicting absorbance values at same wavelength: {absorbance1} vs {absorbance2} "
            f"when rounded to {abs(low_precision_exp)} decimal places."
        )
        raise AllotropeConversionError(msg)

    # Return the value with the highest precision
    return high_precision


def _get_calculated_data_values(
    well_plate_data: SeriesData, wavelength_columns: list[str]
) -> tuple[dict[str, float], list[ErrorDocument]]:
    calculated_data_values: dict[str, float] = {}
    error_documents: list[ErrorDocument] = []
    for wavelength_column in wavelength_columns:
        for item in CALCULATED_DATA_LOOKUP.get(wavelength_column, []):
            value, is_na = _get_calculated_value_and_is_na(
                well_plate_data, item["column"]
            )
            # Only create error docs when the cell is the literal "N/A"
            if is_na:
                error_documents.append(
                    ErrorDocument(
                        error=NOT_APPLICABLE,
                        error_feature=item["name"],
                    )
                )
            # Skip missing cells entirely; include numeric values
            if value is not None:
                calculated_data_values[item["column"]] = value
    return calculated_data_values, error_documents


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
        plate_well_count=96,
        measurements=[_create_measurement(data, header, wavelength_columns)],
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
        metadata_custom_info=_filter_empty_string_values(
            header.get_unread(
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
                    "e1%",
                    "concentration (mg/ml)",
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
            )
        ),
    )


def _filter_empty_string_values(unread: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in unread.items()
        if not (isinstance(value, str) and value.strip() == "")
    }


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
