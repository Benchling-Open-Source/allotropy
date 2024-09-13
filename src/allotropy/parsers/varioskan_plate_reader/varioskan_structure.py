from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Data,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.utils.uuids import random_uuid_str

sample_role_mappings = {
    "Un": SampleRoleType.unknown_sample_role,
    "Std": SampleRoleType.standard_sample_role,
    "Blank": SampleRoleType.blank_role,
    "Ctrl": SampleRoleType.control_sample_role,
}


@dataclass(frozen=True)
class VarioskanMetadata:
    @staticmethod
    def create_metadata(
        instrument_info_df: pd.DataFrame, general_info_df: pd.DataFrame, file_name: str
    ) -> Metadata:
        software_info = None
        for col in general_info_df.columns:
            for value in general_info_df[col].dropna():
                if "SkanIt Software" in str(value):
                    software_info = str(value)
                    break
            if software_info:
                break
        # Regular expression to extract software and version
        pattern = r"(SkanIt Software.*?)(?=,)|(\b\d+\.\d+\.\d+\.\d+\b)"
        matches = re.findall(pattern, software_info)
        # Process matches to get a cleaner output
        software_name = matches[0][0].strip() if matches[0][0] else None
        version_number = matches[1][1] if len(matches) > 1 and matches[1][1] else None

        return Metadata(
            device_identifier=VarioskanMetadata.find_value_by_label(
                instrument_info_df, "Name"
            ),
            model_number=VarioskanMetadata.find_value_by_label(
                instrument_info_df, "Name"
            ),
            software_name=software_name,
            software_version=version_number,
            unc_path="",
            file_name=file_name,
            equipment_serial_number=VarioskanMetadata.find_value_by_label(
                instrument_info_df, "Serial number"
            ),
            device_type="Plate Reader"
            # firmware_version=VarioskanMetadata.find_value_by_label(instrument_info_df, "ESW version")
        )

    # Function to find the value based on the label in the dataframe
    @staticmethod
    def find_value_by_label(df, label):
        row = df[df.iloc[:, 1].str.contains(label, case=False, na=False)]
        if not row.empty:
            return row.iloc[0, 4]  # Assuming the value is in the 5th column (index 4)
        return None


@dataclass(frozen=True)
class AbsorbanceDataWell(Measurement):
    @staticmethod
    def create(
        well_location, abs_value, sample_name, detector_wavelength
    ) -> Measurement:
        return Measurement(
            type_="Absorbance",
            identifier=random_uuid_str(),
            sample_identifier=sample_name,
            location_identifier=well_location,
            sample_role_type=AbsorbanceDataWell.get_sample_role(sample_name),
            absorbance=abs_value,
            detector_wavelength_setting=detector_wavelength,
        )

    @staticmethod
    def get_sample_role(sample_name):
        stripped_text = re.sub(r"\d+", "", sample_name)
        try:
            return sample_role_mappings[stripped_text]
        except KeyError as err:
            msg = f"Unable to identify sample role from {sample_name}"
            raise AllotropyParserError(msg) from err


@dataclass(frozen=True)
class VarioskanMeasurementGroup(MeasurementGroup):
    @staticmethod
    def create(absorbance_sheet_df, layout_definitions_df, session_info_df):
        (
            abs_df,
            name_df,
            wavelength,
        ) = VarioskanMeasurementGroup.identify_abs_and_sample_dfs(absorbance_sheet_df)
        plate_well_count = VarioskanMeasurementGroup.get_plate_well_count(
            layout_definitions_df
        )
        session_name = VarioskanMeasurementGroup.find_value_by_label(
            session_info_df, "Session notes"
        )
        exec_time = VarioskanMeasurementGroup.find_value_by_label(
            session_info_df, "Execution Time"
        )
        absorbance_wells = []
        for index, row in abs_df.iterrows():
            well_letter = row[0]
            for col_name, value in list(row.items())[1:]:
                col_index = abs_df.columns.get_loc(col_name)
                well_name = name_df.iloc[index, col_index]
                abs_value = value
                abs_well = AbsorbanceDataWell.create(
                    well_location=well_letter + str(col_index),
                    abs_value=abs_value,
                    sample_name=well_name,
                    detector_wavelength=wavelength,
                )
                absorbance_wells.append(abs_well)
        return MeasurementGroup(
            measurements=absorbance_wells,
            plate_well_count=plate_well_count,
            _measurement_time=exec_time,
            experimental_data_identifier=session_name,
        )

    @staticmethod
    def get_plate_well_count(layout_definitions_df):
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
        # Extract the integer from the combined string
        plate_template_number = int(
            re.search(r"\d+", plate_template_value).group()
            if plate_template_value
            else None
        )
        return plate_template_number

    @staticmethod
    def identify_abs_and_sample_dfs(absorbance_sheet_df):
        # Initialize variables
        start_reading_abs = False
        start_reading_sample = False
        data_between_abs_and_blank = []
        data_between_sample_and_blank = []

        # Iterate through each row
        for _index, row in absorbance_sheet_df.iterrows():
            if pd.notna(row[0]) and "Wavelength" in row[0]:
                wavelength = int(
                    re.search(r"Wavelength:\s*(\d{3})\s*nm", row[0]).group(1)
                )
            if start_reading_sample:
                # Check if the row is blank
                if row.isnull().all():
                    break
                data_between_sample_and_blank.append(row)
            elif start_reading_abs:
                # Check if the row is blank
                if row.isnull().all():
                    start_reading_abs = False
                    start_reading_sample = False  # Reset this to prevent starting the next DataFrame before finding 'sample'
                else:
                    data_between_abs_and_blank.append(row)
            elif "Abs" in row.values.astype(str):  # Check if 'abs' is in the row
                start_reading_abs = True
            elif "Sample" in row.values.astype(str):  # Check if 'sample' is in the row
                start_reading_sample = True

        # Create DataFrames with the collected data
        df_between_abs_and_blank = pd.DataFrame(data_between_abs_and_blank).reset_index(
            drop=True
        )
        df_between_sample_and_blank = pd.DataFrame(
            data_between_sample_and_blank
        ).reset_index(drop=True)

        return df_between_abs_and_blank, df_between_sample_and_blank, wavelength

    # Function to find the value based on the label in the dataframe
    @staticmethod
    def find_value_by_label(df, label):
        row = df[df.iloc[:, 1].str.contains(label, case=False, na=False)]
        if not row.empty:
            return row.iloc[0, 4]  # Assuming the value is in the 5th column (index 4)
        return None


@dataclass(frozen=True)
class DataVarioskan(Data):
    @staticmethod
    def create(sheet_data: dict[str, pd.DataFrame], file_name: str) -> Data:
        for sheet_name, df in sheet_data.items():
            # NOTE: This assumes a single absorbance plate on a single tab
            if "Absorbance" in sheet_name:
                abs_df = df
            elif "Session information" in sheet_name:
                session_df = df
            elif "Instrument information" in sheet_name:
                inst_info_df = df
            elif "Layout" in sheet_name:
                layout_df = df
            elif "General" in sheet_name:
                general_df = df

        metadata = VarioskanMetadata.create_metadata(
            instrument_info_df=inst_info_df,
            general_info_df=general_df,
            file_name=file_name,
        )
        measurement_group = VarioskanMeasurementGroup.create(
            absorbance_sheet_df=abs_df,
            layout_definitions_df=layout_df,
            session_info_df=session_df,
        )

        return Data(
            metadata=metadata,
            measurement_groups=[measurement_group],
        )
