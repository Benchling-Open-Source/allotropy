import pandas as pd
import pytest

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.exceptions import AllotropyParserError
from allotropy.parsers.varioskan_plate_reader.varioskan_structure import (
    AbsorbanceDataWell,
    DataVarioskan,
    VarioskanMeasurementGroup,
    VarioskanMetadata,
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
    instrument_info_df = pd.DataFrame(data)

    data = {
        "General information": [None, None, "Software version", None],
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
    general_info_df = pd.DataFrame(data)

    varioskan_metadata = VarioskanMetadata.create_metadata(
        instrument_info_df=instrument_info_df,
        general_info_df=general_info_df,
        file_name="test file",
    )

    assert varioskan_metadata.device_identifier == "Varioskan LUX"
    assert varioskan_metadata.equipment_serial_number == "3020-81776"
    assert (
        varioskan_metadata.software_name
        == "SkanIt Software 7.0 RE for Microplate Readers RE"
    )
    assert varioskan_metadata.software_version == "7.0.0.50"


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


def test_create_varioskan_meas_group() -> None:
    file_path = "tests/parsers/varioskan_plate_reader/testdata/skanit_data.xlsx"
    absorbance_df = pd.read_excel(file_path, sheet_name="Absorbance 1_01")
    layout_definitions_df = pd.read_excel(file_path, sheet_name="Layout definitions")
    session_info_df = pd.read_excel(file_path, sheet_name="Session information")

    varioskan_meas_group = VarioskanMeasurementGroup.create(
        absorbance_sheet_df=absorbance_df,
        layout_definitions_df=layout_definitions_df,
        session_info_df=session_info_df,
    )
    assert len(varioskan_meas_group.measurements) == 96
    assert varioskan_meas_group.plate_well_count == 96
    assert (
        varioskan_meas_group.experimental_data_identifier
        == "5. APOE potency MOA_EB_20230522_003"
    )

    assert varioskan_meas_group.measurements[95].location_identifier == "H12"
    assert varioskan_meas_group.measurements[95].absorbance == 0.1032


def test_create_varioskan_data() -> None:
    file_path = "tests/parsers/varioskan_plate_reader/testdata/skanit_data.xlsx"
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
    varioskan_data = DataVarioskan.create(sheet_data=sheet_data, file_name="abc")
    assert len(varioskan_data.measurement_groups) == 1
    assert varioskan_data.metadata.equipment_serial_number == "3020-81776"
