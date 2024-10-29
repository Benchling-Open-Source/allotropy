import pandas as pd
import pytest

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.thermo_skanit.thermo_skanit_structure import (
    AbsorbanceDataWell,
    DataThermoSkanIt,
    ThermoSkanItMeasurementGroups,
    ThermoSkanItMetadata,
)


def test_create_metadata() -> None:
    data = {
        "Instrument information": [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "Unnamed: 1": [
            None,
            "Name",
            "ESW version",
            "Optical response compensation",
            "Serial number",
            None,
            "Instrument modules",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "Unnamed: 2": [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "Module's name",
            "Module's serial number",
            "Plate adapter name",
            "Plate adapter number",
            None,
            "Incubator",
            "Gas control",
            "Top optics",
            "Bottom optics",
            "Dispenser",
        ],
        "Unnamed: 3": [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "Unnamed: 4": [
            None,
            "Varioskan LUX",
            "1.00.38",
            "Yes",
            "3020-81776",
            None,
            None,
            None,
            "LAT module",
            "LL2214801",
            "96-well adapter for plate without lid",
            "2",
            None,
            "Yes",
            "No",
            "Yes",
            "No",
            "No",
        ],
    }
    # Creating the DataFrame
    instrument_info_df = DataThermoSkanIt._clean_dataframe(pd.DataFrame(data))

    data = {
        "General information": [None, None, None, None],
        "Unnamed: 1": [None, "Report generated with SW version", None, None],
        "Unnamed: 2": [None, None, None, None],
        "Unnamed: 3": [None, None, None, None],
        "Unnamed: 4": [
            None,
            "SkanIt Software 7.0 RE for Microplate Readers RE, ver. 7.0.0.50",
            None,
            None,
        ],
    }

    # Create the DataFrame
    general_info_df = DataThermoSkanIt._clean_dataframe(pd.DataFrame(data))

    skanit_metadata = ThermoSkanItMetadata.create_metadata(
        instrument_info_df=instrument_info_df,
        general_info_df=general_info_df,
        file_path="test_file",
    )

    assert skanit_metadata.device_identifier == "Varioskan LUX"
    assert skanit_metadata.equipment_serial_number == "3020-81776"
    assert (
        skanit_metadata.software_name
        == "SkanIt Software 7.0 RE for Microplate Readers RE"
    )
    assert skanit_metadata.software_version == "7.0.0.50"


def test_get_sample_role() -> None:
    sample_name_1 = "Std392"
    sample_name_2 = "Un4"

    assert (
        AbsorbanceDataWell.get_sample_role(sample_name_1)
        == SampleRoleType.standard_sample_role
    )
    assert (
        AbsorbanceDataWell.get_sample_role(sample_name_2)
        == SampleRoleType.unknown_sample_role
    )


def test_get_sample_role_failure() -> None:
    sample_name_error = "Unk4"
    with pytest.raises(
        AllotropyParserError, match="Unable to identify sample role from"
    ):
        AbsorbanceDataWell.get_sample_role(sample_name_error)


def test_create_skanit_meas_group() -> None:
    file_path = "tests/parsers/thermo_skanit/testdata/skanit_data.xlsx"
    absorbance_df = DataThermoSkanIt._clean_dataframe(
        pd.read_excel(file_path, sheet_name="Absorbance 1_01")
    )
    layout_definitions_df = DataThermoSkanIt._clean_dataframe(
        pd.read_excel(file_path, sheet_name="Layout definitions")
    )
    session_info_df = DataThermoSkanIt._clean_dataframe(
        pd.read_excel(file_path, sheet_name="Session information")
    )

    skanit_meas_group = ThermoSkanItMeasurementGroups.create(
        absorbance_sheet_df=absorbance_df,
        layout_definitions_df=layout_definitions_df,
        session_info_df=session_info_df,
    )
    assert len(skanit_meas_group) == 96
    assert skanit_meas_group[0].plate_well_count == 96
    assert (
        skanit_meas_group[0].experimental_data_identifier
        == "5. APOE potency MOA_EB_20230522_003"
    )

    assert skanit_meas_group[95].measurements[0].location_identifier == "H12"
    assert skanit_meas_group[95].measurements[0].absorbance == 0.1032


def test_create_skanit_data() -> None:
    file_path = "tests/parsers/thermo_skanit/testdata/skanit_data.xlsx"
    sheet_data = {
        "Absorbance 1_01": pd.read_excel(file_path, sheet_name="Absorbance 1_01"),
        "General information": pd.read_excel(
            file_path, sheet_name="General information"
        ),
        "Session information": pd.read_excel(
            file_path, sheet_name="Session information"
        ),
        "Instrument information": pd.read_excel(
            file_path, sheet_name="Instrument information"
        ),
        "Layout definitions": pd.read_excel(file_path, sheet_name="Layout definitions"),
    }
    skanit_data = DataThermoSkanIt.create(sheet_data=sheet_data, file_path="abc")
    assert len(skanit_data.measurement_groups) == 96
    assert skanit_data.metadata.equipment_serial_number == "3020-81776"
