from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, TypedDict

import numpy as np
import pandas as pd

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    Data,
    ErrorDocument,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.constants import NEGATIVE_ZERO, NOT_APPLICABLE
from allotropy.parsers.thermo_skanit.constants import DEVICE_TYPE, SAMPLE_ROLE_MAPPINGS
from allotropy.parsers.utils.pandas import df_to_series_data, parse_header_row
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none

MEASUREMENT_TYPES = {
    MeasurementType.ULTRAVIOLET_ABSORBANCE: "Absorbance",
    MeasurementType.FLUORESCENCE: "Fluorescence",
    MeasurementType.LUMINESCENCE: "Luminescence",
}

SHEET_TABS = [
    "Session information",
    "Instrument information",
    "Layout definitions",
    "General information",
]

GENERAL_INFO_KEYS = [
    "software_name",
    "software_version",
]


class PlateDict(TypedDict):
    wavelength_data: dict[float, pd.DataFrame]
    sample_data: pd.DataFrame


@dataclass(frozen=True)
class PlateData:
    plate_identifier: str
    wavelength_data: dict[float, pd.DataFrame]
    sample_data: pd.DataFrame

    @staticmethod
    def create(
        plate_identifier: str,
        wavelength_data: dict[float, pd.DataFrame],
        sample_data: pd.DataFrame,
    ) -> PlateData:
        return PlateData(
            plate_identifier=plate_identifier,
            wavelength_data=wavelength_data,
            sample_data=sample_data,
        )


@dataclass(frozen=True)
class ThermoSkanItMetadata:
    @staticmethod
    def create_metadata(
        file_path: str,
        instrument_info_df: pd.DataFrame | None,
        general_info_df: pd.DataFrame | None,
    ) -> Metadata:
        instrument_info_data = ThermoSkanItMetadata._get_instrument_data(
            instrument_info_df
        )
        general_info_data = ThermoSkanItMetadata._get_general_info_data(general_info_df)
        path = Path(file_path)
        return Metadata(
            asm_file_identifier=path.with_suffix(".json").name,
            data_system_instance_id=NOT_APPLICABLE,
            file_name=path.name,
            unc_path=file_path,
            device_identifier=instrument_info_data["device_identifier"],
            model_number=instrument_info_data["model_number"],
            equipment_serial_number=instrument_info_data.get("equipment_serial_number"),
            software_name=general_info_data["software_name"],
            software_version=general_info_data["software_version"],
        )

    @staticmethod
    def _get_general_info_data(
        general_info_df: pd.DataFrame | None,
    ) -> dict[str, str | None]:
        if general_info_df is None:
            return dict.fromkeys(GENERAL_INFO_KEYS, None)

        general_info_data = df_to_series_data(parse_header_row(general_info_df.T))
        software_info = general_info_data.get(str, "Report generated with SW version")
        if not software_info:
            return dict.fromkeys(GENERAL_INFO_KEYS, NOT_APPLICABLE)
        software_name, software_version_txt = software_info.split(",", 1)
        match = re.search(r"\d+(?:\.\d+)*", software_version_txt)
        software_version = match.group() if match else None
        return {
            "software_name": software_name,
            "software_version": software_version,
        }

    @staticmethod
    def _get_instrument_data(
        instrument_info_df: pd.DataFrame | None,
    ) -> dict[str, str]:
        if instrument_info_df is None:
            return {
                "device_identifier": NOT_APPLICABLE,
                "model_number": NOT_APPLICABLE,
            }

        # Replace empty with "" so we can add label columns together
        instrument_info_df = instrument_info_df.fillna("")

        # The labels for data is spread across the first two columns for some reason, combine them as index.
        # NOTE: This is an assumption that may not be true for future files
        # Combine the first two columns into a Series
        combined_series = instrument_info_df.iloc[:, 0] + instrument_info_df.iloc[:, 1]
        # Convert the Series to an Index
        instrument_info_df.index = pd.Index(combined_series)

        # Read data from the last column, this is where values are found
        instrument_info_data = df_to_series_data(instrument_info_df.T, index=-1)

        lookups = {
            "device_identifier": ("Name", NOT_APPLICABLE),
            "model_number": ("Name", NOT_APPLICABLE),
            "equipment_serial_number": ("Serial number", None),
        }
        return {
            key: value
            for key, (label, default) in lookups.items()
            if (value := instrument_info_data.get(str, label, default)) is not None
        }


@dataclass
class DataWell(Measurement):
    @staticmethod
    def create(
        well_location: str,
        value: float,
        sample_name: str,
        type_: MeasurementType,
        detector_wavelength: float | None,
        well_plate_identifier: str | None,
        error_documents: list[ErrorDocument] | None = None,
        experimental_data_identifier: str | None = None,
    ) -> Measurement:
        measurement_type_str = MEASUREMENT_TYPES[type_]
        error_docs = error_documents or []

        return Measurement(
            type_=type_,
            identifier=random_uuid_str(),
            sample_identifier=sample_name,
            location_identifier=well_location,
            sample_role_type=DataWell.get_sample_role(sample_name),
            detector_wavelength_setting=detector_wavelength,
            device_type=DEVICE_TYPE,
            detection_type=measurement_type_str,
            well_plate_identifier=well_plate_identifier,
            absorbance=value
            if measurement_type_str
            == MEASUREMENT_TYPES[MeasurementType.ULTRAVIOLET_ABSORBANCE]
            else None,
            fluorescence=value
            if measurement_type_str == MEASUREMENT_TYPES[MeasurementType.FLUORESCENCE]
            else None,
            luminescence=value
            if measurement_type_str == MEASUREMENT_TYPES[MeasurementType.LUMINESCENCE]
            else None,
            experimental_data_identifier=experimental_data_identifier,
            error_document=error_docs if error_docs else None,
        )

    @staticmethod
    def get_sample_role(sample_name: str) -> SampleRoleType | None:
        stripped_text = re.sub(r"\d+", "", sample_name)
        try:
            return SAMPLE_ROLE_MAPPINGS[stripped_text]
        except KeyError as _:
            return None


@dataclass(frozen=True)
class ThermoSkanItMeasurementGroups:
    @staticmethod
    def create(
        sheet_df: pd.DataFrame,
        type_: MeasurementType,
        session_info_df: pd.DataFrame | None,
    ) -> list[MeasurementGroup]:
        plates = ThermoSkanItMeasurementGroups.identify_data_and_sample_dfs(sheet_df)

        session_name = exec_time = None
        if session_info_df is not None:
            session_info_data = df_to_series_data(parse_header_row(session_info_df.T))
            session_name = session_info_data.get(str, "Session name")
            exec_time = session_info_data.get(str, "Execution time")

        if not exec_time:
            exec_time = sheet_df.iloc[1].iloc[0]

        if not exec_time:
            msg = "Execution time not found"
            raise AllotropyParserError(msg)

        if not session_name:
            experiment = sheet_df.iloc[0].iloc[0]
            session_name = experiment.replace(".skax", "") if experiment else None

        well_measurements: dict[tuple[str, str], list[Measurement]] = {}
        plate_well_counts: dict[str, int] = {}

        for plate in plates:
            for wavelength, data_df in plate.wavelength_data.items():
                if data_df.empty:
                    continue

                valid_rows = ~pd.isnull(data_df.index) & (data_df.index != "")
                valid_cols = ~pd.isnull(data_df.columns) & (data_df.columns != "")
                plate_well_count = len(data_df.index[valid_rows]) * len(
                    data_df.columns[valid_cols]
                )

                data_df.dropna(how="all", inplace=True)

                stacked = data_df.stack()

                for well_letter, well_column in stacked.index:
                    well_location = well_letter + str(well_column)
                    well_key = (plate.plate_identifier, well_location)

                    if not plate.sample_data.empty:
                        sample_name = plate.sample_data.loc[well_letter, well_column]
                    else:
                        sample_name = f"{plate.plate_identifier}_{well_location}"

                    measurement_value = stacked.loc[well_letter, well_column]
                    error_docs = []

                    if not try_float_or_none(measurement_value):
                        error_value = str(measurement_value)
                        error_docs.append(
                            ErrorDocument(
                                error=error_value,
                                error_feature=MEASUREMENT_TYPES[type_],
                            )
                        )
                        measurement_value = NEGATIVE_ZERO

                    well = DataWell.create(
                        well_location=well_location,
                        value=measurement_value,
                        sample_name=sample_name,
                        detector_wavelength=wavelength if wavelength > 0 else None,
                        type_=type_,
                        well_plate_identifier=plate.plate_identifier,
                        error_documents=error_docs if error_docs else None,
                        experimental_data_identifier=session_name.replace(".skax", "")
                        if session_name
                        else None,
                    )

                    if well_key not in well_measurements:
                        well_measurements[well_key] = []
                    well_measurements[well_key].append(well)

            plate_well_counts[plate.plate_identifier] = plate_well_count

        meas_groups = []
        for (plate_id, _), measurements in well_measurements.items():
            meas_groups.append(
                MeasurementGroup(
                    measurements=measurements,
                    plate_well_count=plate_well_counts[plate_id],
                    measurement_time=exec_time,
                )
            )

        return meas_groups

    @staticmethod
    def _set_headers(df: pd.DataFrame) -> pd.DataFrame:
        # Set the first column (well letters) as the index
        df.set_index(df.columns[0], inplace=True)
        # Set the first row (well numbers) as the columns
        df = parse_header_row(df)
        valid_columns = pd.notna(df.columns) & (
            df.columns.astype(str).str.lower() != "nan"
        )
        df = df[df.columns[valid_columns]]
        # Cast row numbers to int (float first to handle decimals, e.g. 1.0)
        df.columns = df.columns.astype(float).astype(int)
        return df

    @staticmethod
    def identify_data_and_sample_dfs(
        absorbance_sheet_df: pd.DataFrame,
    ) -> list[PlateData]:
        """Parse multiple plates from sheet data, each with multiple wavelengths."""
        plates_dict: dict[str, PlateDict] = {}
        current_plate_id = None
        current_wavelength = None
        current_data_section: list[pd.Series[Any]] = []
        current_sample_section: list[pd.Series[Any]] = []
        reading_data = False
        reading_samples = False

        for _idx, row in absorbance_sheet_df.iterrows():
            row_str = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""

            if "Wavelength:" in row_str:
                wavelength_match = re.search(r"Wavelength:\s*(\d{1,3})\s*nm", row_str)
                if wavelength_match:
                    if (
                        current_wavelength is not None
                        and current_data_section
                        and current_plate_id
                    ):
                        data_df = ThermoSkanItMeasurementGroups._set_headers(
                            pd.DataFrame(current_data_section)
                        )
                        if current_plate_id not in plates_dict:
                            plates_dict[current_plate_id] = {
                                "wavelength_data": {},
                                "sample_data": pd.DataFrame(),
                            }
                        wavelength_data = plates_dict[current_plate_id][
                            "wavelength_data"
                        ]
                        wavelength_data[current_wavelength] = data_df

                    current_wavelength = float(wavelength_match.group(1))
                    current_data_section = []
                    reading_data = False
                    reading_samples = False
                    continue

            if "Plate" in row_str:
                plate_match = re.search(r"Plate\s*(\d+)", row_str)
                if plate_match:
                    current_plate_id = plate_match.group(0)
                    if current_plate_id not in plates_dict:
                        plates_dict[current_plate_id] = {
                            "wavelength_data": {},
                            "sample_data": pd.DataFrame(),
                        }
                    continue

            if "Abs" in row.values.astype(str) or "RLU" in row.values.astype(str):
                reading_data = True
                reading_samples = False
                current_data_section = [row]
                continue

            if "Sample" in row.values.astype(str):
                if (
                    current_wavelength is not None
                    and current_data_section
                    and current_plate_id
                ):
                    data_df = ThermoSkanItMeasurementGroups._set_headers(
                        pd.DataFrame(current_data_section)
                    )
                    wavelength_data = plates_dict[current_plate_id]["wavelength_data"]
                    wavelength_data[current_wavelength] = data_df

                reading_samples = True
                reading_data = False
                current_sample_section = [row]
                continue

            if reading_data:
                current_data_section.append(row)
            elif reading_samples:
                current_sample_section.append(row)

                if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == "":
                    if current_sample_section and current_plate_id:
                        sample_df = ThermoSkanItMeasurementGroups._set_headers(
                            pd.DataFrame(current_sample_section[:-1])
                        )
                        plates_dict[current_plate_id]["sample_data"] = sample_df
                        current_sample_section = []
                        reading_samples = False

        if current_wavelength is not None and current_data_section and current_plate_id:
            data_df = ThermoSkanItMeasurementGroups._set_headers(
                pd.DataFrame(current_data_section)
            )
            wavelength_data = plates_dict[current_plate_id]["wavelength_data"]
            wavelength_data[current_wavelength] = data_df

        if current_sample_section and current_plate_id:
            sample_df = ThermoSkanItMeasurementGroups._set_headers(
                pd.DataFrame(current_sample_section)
            )
            plates_dict[current_plate_id]["sample_data"] = sample_df

        plates = []
        for plate_id, plate_info in plates_dict.items():
            plates.append(
                PlateData.create(
                    plate_identifier=plate_id,
                    wavelength_data=plate_info["wavelength_data"],
                    sample_data=plate_info["sample_data"],
                )
            )

        return plates


@dataclass(frozen=True)
class DataThermoSkanIt(Data):
    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        # Prevent pandas from silently downcasting values, to prevent future incompatibility.
        pd.set_option("future.no_silent_downcasting", True)  # noqa: FBT003
        df = df.replace(r"^\s*$", np.nan, regex=True)
        df = df.dropna(axis="index", how="all")
        df = df.dropna(axis="columns", how="all")
        return df

    @staticmethod
    def create(sheet_data: dict[str, pd.DataFrame], file_path: str) -> Data:
        measurement_df = _type = None
        clean_data = {
            key: DataThermoSkanIt._clean_dataframe(sheet_data[key])
            for key in sheet_data.keys()
            if key in SHEET_TABS
        }
        for measurement_type, measurement_type_key in MEASUREMENT_TYPES.items():
            for sheet_name, df in sheet_data.items():
                if measurement_type_key in sheet_name:
                    measurement_df = df
                    _type = measurement_type
                    break

        if measurement_df is None or measurement_df.empty or _type is None:
            msg = "Unsupported or missing measurement type"
            raise AllotropyParserError(msg)
        metadata = ThermoSkanItMetadata.create_metadata(
            instrument_info_df=clean_data.get("Instrument information"),
            general_info_df=clean_data.get("General information"),
            file_path=file_path,
        )
        measurement_groups = ThermoSkanItMeasurementGroups.create(
            sheet_df=measurement_df,
            session_info_df=clean_data.get("Session information"),
            type_=_type,
        )

        return Data(
            metadata=metadata,
            measurement_groups=measurement_groups,
        )
