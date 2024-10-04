from __future__ import annotations

from dataclasses import dataclass
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
from allotropy.parsers.thermo_skanit.constants import DEVICE_TYPE, SAMPLE_ROLE_MAPPINGS
from allotropy.parsers.utils.pandas import df_to_series_data, parse_header_row
from allotropy.parsers.utils.uuids import random_uuid_str


@dataclass(frozen=True)
class ThermoSkanItMetadata:
    @staticmethod
    def create_metadata(
        instrument_info_df: pd.DataFrame, general_info_df: pd.DataFrame, file_name: str
    ) -> Metadata:

        # Replace empty with "" so we can add label columns together.
        instrument_info_df = instrument_info_df.fillna("")
        # The labels for data is spread across the first two columns for some reason, combine them as index.
        # NOTE: This is an assumption that may not be true for future files
        # Combine the first two columns into a Series
        combined_series = instrument_info_df.iloc[:, 0] + instrument_info_df.iloc[:, 1]
        # Convert the Series to an Index
        instrument_info_df.index = pd.Index(combined_series)
        # Read data from the last column, this is where values are found
        instrument_info_data = df_to_series_data(instrument_info_df.T, index=-1)
        general_info_data = df_to_series_data(parse_header_row(general_info_df.T))
        software_info = general_info_data.get(str, "Report generated with SW version")
        # Regular expression to extract software and version
        pattern = r"(SkanIt Software.*?)(?=,)|(\b\d+\.\d+\.\d+\.\d+\b)"
        if software_info is not None:
            matches = re.findall(pattern, software_info)
            # Process matches to get a cleaner output
            software_name = matches[0][0].strip() if matches[0][0] else None
            version_number = (
                matches[1][1] if len(matches) > 1 and matches[1][1] else None
            )
        else:
            msg = "Unable to identify Software Name or Version from General information tab"
            raise AllotropyParserError(msg)

        return Metadata(
            device_identifier=instrument_info_data[str, "Name"],
            model_number=instrument_info_data[str, "Name"],
            software_name=software_name,
            software_version=version_number,
            unc_path="",
            file_name=file_name,
            equipment_serial_number=instrument_info_data.get(str, "Serial number"),
        )


@dataclass(frozen=True)
class AbsorbanceDataWell(Measurement):
    @staticmethod
    def create(
        well_location: str,
        abs_value: float,
        sample_name: str,
        detector_wavelength: float,
    ) -> Measurement:
        return Measurement(
            type_=MeasurementType.ULTRAVIOLET_ABSORBANCE,
            identifier=random_uuid_str(),
            sample_identifier=sample_name,
            location_identifier=well_location,
            sample_role_type=AbsorbanceDataWell.get_sample_role(sample_name),
            absorbance=abs_value,
            detector_wavelength_setting=detector_wavelength,
            device_type=DEVICE_TYPE,
        )

    @staticmethod
    def get_sample_role(sample_name: str) -> SampleRoleType:
        stripped_text = re.sub(r"\d+", "", sample_name)
        try:
            return SAMPLE_ROLE_MAPPINGS[stripped_text]
        except KeyError as err:
            msg = f"Unable to identify sample role from {sample_name}"
            raise AllotropyParserError(msg) from err


@dataclass(frozen=True)
class ThermoSkanItMeasurementGroups:
    @staticmethod
    def create(
        absorbance_sheet_df: pd.DataFrame,
        layout_definitions_df: pd.DataFrame,
        session_info_df: pd.DataFrame,
    ) -> list[MeasurementGroup]:
        (
            abs_df,
            name_df,
            wavelength,
        ) = ThermoSkanItMeasurementGroups.identify_abs_and_sample_dfs(
            absorbance_sheet_df
        )
        plate_well_count = ThermoSkanItMeasurementGroups.get_plate_well_count(
            layout_definitions_df
        )

        session_info_data = df_to_series_data(parse_header_row(session_info_df.T))
        session_name = session_info_data.get(str, "Session notes")
        exec_time = session_info_data[str, "Execution time"]

        meas_groups = []
        # Stack the DataFrame, creating a MultiIndex
        stacked = abs_df.stack()

        # Iterate through the MultiIndex series and unpack it correctly
        for well_letter, well_column in stacked.index:
            abs_well = AbsorbanceDataWell.create(
                well_location=well_letter + str(well_column),
                abs_value=stacked.loc[well_letter, well_column],
                sample_name=str(name_df.loc[well_letter, well_column]),
                detector_wavelength=wavelength,
            )
            meas_groups.append(
                MeasurementGroup(
                    measurements=[abs_well],
                    plate_well_count=plate_well_count,
                    measurement_time=exec_time,
                    experimental_data_identifier=session_name,
                )
            )
        return meas_groups

    @staticmethod
    def get_plate_well_count(layout_definitions_df: pd.DataFrame) -> int:
        # Combine all non-empty values in the row where "Plate template" is found
        plate_template_row = layout_definitions_df[
            layout_definitions_df.iloc[:, 0].str.contains(
                "Plate template", case=False, na=False
            )
        ]
        plate_template_value = (
            plate_template_row.iloc[0].dropna().str.cat(sep=" ")
            if not plate_template_row.empty
            else None
        )
        msg = (
            "Unable to identify plate well count from Layout definitions tab. "
            "Expected to find in Plate template description."
        )
        if plate_template_value is None:
            raise AllotropyParserError(msg)
        else:
            # Extract the integer from the combined string
            search_string = re.search(r"\d+", plate_template_value)
            if search_string:
                plate_template_number = int(search_string.group())
                return plate_template_number
            else:
                raise AllotropyParserError(msg)

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
    def identify_abs_and_sample_dfs(
        absorbance_sheet_df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame, float]:
        # Initialize variables
        start_reading_abs = False
        start_reading_sample = False
        data_between_abs_and_blank = []
        data_between_sample_and_blank = []

        # Iterate through each row
        for _, row in absorbance_sheet_df.iterrows():
            if pd.notna(row.iloc[0]) and "Wavelength" in row.iloc[0]:
                match = re.search(r"Wavelength:\s*(\d{3})\s*nm", row.iloc[0])
                if match:
                    wavelength = float(match.group(1))
                else:
                    msg = "Unable to identify Wavelength (nm) from Absorbance tab"
                    raise AllotropyParserError(msg)
            if "Abs" in row.values.astype(str):  # Check if 'abs' is in the row
                start_reading_abs = True
            if "Sample" in row.values.astype(str):  # Check if 'sample' is in the row
                start_reading_sample = True
            if pd.notna(row.iloc[0]) and "Autoloading" in row.iloc[0]:
                break

            if start_reading_sample:
                data_between_sample_and_blank.append(row)
            elif start_reading_abs:
                data_between_abs_and_blank.append(row)

        # Create DataFrames with the collected data
        df_between_abs_and_blank = ThermoSkanItMeasurementGroups._set_headers(
            pd.DataFrame(data_between_abs_and_blank)
        )
        df_between_sample_and_blank = ThermoSkanItMeasurementGroups._set_headers(
            pd.DataFrame(data_between_sample_and_blank)
        )

        return (df_between_abs_and_blank, df_between_sample_and_blank, wavelength)


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
    def create(sheet_data: dict[str, pd.DataFrame], file_name: str) -> Data:
        for sheet_name, df in sheet_data.items():
            clean_df = DataThermoSkanIt._clean_dataframe(df)
            # NOTE: This assumes a single absorbance plate on a single tab
            if "Absorbance" in sheet_name:
                abs_df = clean_df
            elif "Session information" in sheet_name:
                session_df = clean_df
            elif "Instrument information" in sheet_name:
                inst_info_df = clean_df
            elif "Layout" in sheet_name:
                layout_df = clean_df
            elif "General" in sheet_name:
                general_df = clean_df

        metadata = ThermoSkanItMetadata.create_metadata(
            instrument_info_df=inst_info_df,
            general_info_df=general_df,
            file_name=file_name,
        )
        measurement_groups = ThermoSkanItMeasurementGroups.create(
            absorbance_sheet_df=abs_df,
            layout_definitions_df=layout_df,
            session_info_df=session_df,
        )

        return Data(
            metadata=metadata,
            measurement_groups=measurement_groups,
        )
