from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.thermo_skanit.constants import DEVICE_TYPE, SAMPLE_ROLE_MAPPINGS
from allotropy.parsers.utils.pandas import df_to_series_data, parse_header_row
from allotropy.parsers.utils.uuids import random_uuid_str

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
        return Metadata(
            file_name=Path(file_path).name,
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


@dataclass(frozen=True)
class DataWell(Measurement):
    @staticmethod
    def create(
        well_location: str,
        value: float,
        sample_name: str,
        type_: MeasurementType,
        detector_wavelength: float | None,
        well_plate_identifier: str | None,
    ) -> Measurement:
        measurement_type_str = MEASUREMENT_TYPES[type_]
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
        layout_definitions_df: pd.DataFrame | None,
        session_info_df: pd.DataFrame | None,
    ) -> list[MeasurementGroup]:
        (
            data_df,
            name_df,
            wavelength,
            well_plate_identifier,
        ) = ThermoSkanItMeasurementGroups.identify_data_and_sample_dfs(sheet_df)
        data_df.dropna(how="all", inplace=True)
        plate_well_count = None
        if layout_definitions_df is not None:
            plate_well_count = ThermoSkanItMeasurementGroups.get_plate_well_count(
                layout_definitions_df
            )
        if not plate_well_count:
            plate_well_count = data_df.size

        session_name = exec_time = None
        if session_info_df is not None:
            session_info_data = df_to_series_data(parse_header_row(session_info_df.T))
            session_name = session_info_data.get(str, "Session notes")
            exec_time = session_info_data.get(str, "Execution time")

        if not exec_time:
            exec_time = sheet_df.iloc[1].iloc[0]

        if not exec_time:
            msg = "Execution time not found"
            raise AllotropyParserError(msg)

        if not session_name:
            experiment = sheet_df.iloc[0].iloc[0]
            session_name = experiment.replace(".skax", "") if experiment else None

        meas_groups = []
        # Stack the DataFrame, creating a MultiIndex
        stacked = data_df.stack()

        # Iterate through the MultiIndex series and unpack it correctly
        for well_letter, well_column in stacked.index:
            if not name_df.empty:
                sample_name = name_df.loc[well_letter, well_column]
            else:
                sample_name = f"{well_plate_identifier}_{well_letter}{well_column}"
            well = DataWell.create(
                well_location=well_letter + str(well_column),
                value=stacked.loc[well_letter, well_column],
                sample_name=sample_name,
                detector_wavelength=wavelength,
                type_=type_,
                well_plate_identifier=well_plate_identifier,
            )
            meas_groups.append(
                MeasurementGroup(
                    measurements=[well],
                    plate_well_count=plate_well_count,
                    measurement_time=exec_time,
                    experimental_data_identifier=session_name,
                )
            )
        return meas_groups

    @staticmethod
    def get_plate_well_count(layout_definitions_df: pd.DataFrame) -> int | None:
        # Find row containing "Plate template"
        plate_row = layout_definitions_df[
            layout_definitions_df.iloc[:, 0].str.contains(
                "Plate template", case=False, na=False
            )
        ]

        if plate_row.empty:
            return None

        # Combine all non-empty values in the row
        combined_value = plate_row.iloc[0].dropna().str.cat(sep=" ")

        # Extract first number found
        if match := re.search(r"\d+", combined_value):
            return int(match.group())

        return None

    @staticmethod
    def _set_headers(df: pd.DataFrame) -> pd.DataFrame:
        # Set the first column (well letters) as the index
        df.set_index(df.columns[0], inplace=True)
        # Set the first row (well numbers) as the columns
        df = parse_header_row(df)
        # Cast row numbers to int (float first to handle decimals, e.g. 1.0)
        df.columns = df.columns.astype(float).astype(int)
        return df

    @staticmethod
    def identify_data_and_sample_dfs(
        absorbance_sheet_df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame, float | None, str | None]:
        # Initialize variables
        start_reading_data = False
        start_reading_sample = False
        data_between_abs_and_blank = []
        data_between_sample_and_blank = []
        wavelength = None
        well_plate_identifier = None

        # Iterate through each row
        for _, row in absorbance_sheet_df.iterrows():
            if pd.notna(row.iloc[0]) and "Wavelength" in row.iloc[0]:
                match = re.search(r"Wavelength:\s*(\d{1,3})\s*nm", row.iloc[0])
                if match and (val := float(match.group(1))) != 0:
                    wavelength = val
            if pd.notna(row.iloc[0]) and "Plate" in row.iloc[0]:
                match = re.search(r"Plate\s*(\d)", row.iloc[0])
                if match:
                    well_plate_identifier = match.group(0)
            if "Abs" in row.values.astype(str) or "RLU" in row.values.astype(str):
                start_reading_data = True
            if "Sample" in row.values.astype(str):
                start_reading_sample = True

            if start_reading_sample:
                data_between_sample_and_blank.append(row)
            elif start_reading_data:
                data_between_abs_and_blank.append(row)

        # Create DataFrames with the collected data
        df_between_abs_and_blank = ThermoSkanItMeasurementGroups._set_headers(
            pd.DataFrame(data_between_abs_and_blank)
        )
        if data_between_sample_and_blank:
            df_between_sample_and_blank = ThermoSkanItMeasurementGroups._set_headers(
                pd.DataFrame(data_between_sample_and_blank)
            )
        else:
            df_between_sample_and_blank = pd.DataFrame()

        return (
            df_between_abs_and_blank,
            df_between_sample_and_blank,
            wavelength,
            well_plate_identifier,
        )


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
            layout_definitions_df=clean_data.get("Layout definitions"),
            session_info_df=clean_data.get("Session information"),
            type_=_type,
        )

        return Data(
            metadata=metadata,
            measurement_groups=measurement_groups,
        )
