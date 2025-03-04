from functools import partial
from io import StringIO
from unittest.mock import MagicMock, patch

import pandas as pd

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.bmg_labtech_smart_control.bmg_labtech_smart_control_reader import (
    BmgLabtechSmartControlReader,
    SheetNames,
)
from allotropy.parsers.bmg_labtech_smart_control.bmg_labtech_smart_control_structure import (
    create_calculated_data_documents,
    map_measurement_group,
)
from allotropy.parsers.utils.pandas import map_rows


def _load_data() -> dict[str, pd.DataFrame]:
    return {
        SheetNames.PROTOCOL_INFORMATION.value: pd.DataFrame(
            [
                ["User: user"],
                ["Path: test/path"],
                ["Test ID: 9"],
                ["Test Name: Quant-iT_96 Pico/RiboGreen"],
                ["Date: 11/6/2024"],
                ["Time: 11:14:00 AM"],
                ["ID1: RiboGreen NB-user-5097655-0067"],
                ["ID2: 11/6/2024,12:40:58 PM"],
                ["ID3: Plate 3"],
                ["Fluorescence (FI)"],
                [" Basic settings "],
                ["Measurement type", "Fluorescence (FI)"],
                ["Microplate name", "NUNC 96"],
                [" Endpoint settings "],
                ["No. of flashes per well", "20"],
                [" Optic settings "],
                ["Presetname", "Fluorescein (FITC) *"],
                ["Excitation", "480-14"],
                ["Dichroic filter", "auto 496"],
                ["Emission", "520-30"],
                ["Gain obtained by", "enhanced dynamic range"],
                [
                    "Focal height obtained by",
                    "previous focal height (obtained using auto focus)",
                ],
                ["Focal height  [mm]", "5.9"],
                ["Well used for focus adjustment", "D9"],
                [" General settings "],
                ["Top optic used"],
                ["Spoon type", "automatic"],
                ["Injection needle holder type", "-"],
                ["Settling time [s]", "0.2"],
                [
                    "Reading direction",
                    "bidirectional, horizontal left to right, top to bottom",
                ],
                ["Target temperature [°C]", "set off"],
                ["Target concentration O2 [%]", "set off"],
                ["Target concentration CO2 [%]", "set off"],
            ],
            columns=[0, 1],
        ),
        SheetNames.TABLE_END_POINT.value: pd.DataFrame(
            [
                ["Well", "A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1"],
                [
                    "Content",
                    "Standard S1",
                    "Standard X1",
                    "Sample X2",
                    "Sample X2",
                    "Standard",
                    "Standard",
                    "Blank B",
                    "Blank B",
                ],
                [
                    "Standard Concentration [ng/mL]",
                    "1000",
                    "1000",
                    "250",
                    None,
                    "500",
                    "250",
                    None,
                    None,
                ],
                ["Dilutions", "1", "1", "1", "1", "1", "1", "1", "1"],
                [
                    " Raw Data (480-14/520-30)",
                    "48516",
                    "65626",
                    "64665",
                    "65626",
                    "62353",
                    "336565",
                    "353532",
                    "335326",
                ],
                [
                    " Blank corrected based on Raw Data (480-14/520-30)",
                    "365695",
                    "356465",
                    "2345653",
                    "356561",
                    "545425",
                    "5625636",
                    "326524",
                    "235645",
                ],
            ]
        ),
        SheetNames.MICROPLATE_END_POINT.value: pd.DataFrame(
            [
                [
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
                    "Used correction value(s)",
                ],
                [
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
                    "Blank    28888.33333",
                ],
            ]
        ),
    }


@patch(
    "allotropy.parsers.bmg_labtech_smart_control.bmg_labtech_smart_control_reader.read_multisheet_excel"
)
def test_bmg_labtech_smart_control_reader(mock_read_excel: MagicMock) -> None:
    mock_read_excel.return_value = _load_data()
    reader = BmgLabtechSmartControlReader(
        NamedFileContents(contents=StringIO(""), original_file_path="tmp.txt")
    )
    measurement_groups = map_rows(
        reader.data, partial(map_measurement_group, headers=reader.header)
    )
    calculated_data = create_calculated_data_documents(measurement_groups, reader)
    assert len(measurement_groups) == 8
    assert measurement_groups[0].analyst == "user"
    assert measurement_groups[0].measurement_time == "11/6/2024 11:14:00 AM"
    assert (
        measurement_groups[0].experimental_data_identifier
        == "RiboGreen NB-user-5097655-0067"
    )
    assert measurement_groups[0].experiment_type == "Quant-iT_96 Pico/RiboGreen"
    assert measurement_groups[0].plate_well_count == 96
    measurement = measurement_groups[0].measurements[0]
    assert measurement.fluorescence == 48516
    assert measurement.sample_identifier == "Standard S1"
    assert measurement.sample_role_type == SampleRoleType.standard_sample_role
    assert measurement.location_identifier == "A1"
    assert measurement.well_plate_identifier == "Plate 3"
    assert measurement.device_type == "fluorescence detector"
    assert measurement.detection_type == "fluorescence"
    assert measurement.detector_distance_setting == 5.9
    assert measurement.detector_bandwidth_setting == 30
    assert calculated_data is not None
    assert len(calculated_data) == 7
    assert calculated_data[0].name == "Average of all blanks used"
    assert calculated_data[0].value == 28888.33333
    assert calculated_data[0].unit == "RFU"
    assert len(calculated_data[0].data_sources) == 2
    assert (
        calculated_data[1].name == "Blank corrected based on Raw Data (480-14/520-30)"
    )
    assert calculated_data[1].value == 365695
    assert calculated_data[1].unit == "RFU"
    assert len(calculated_data[1].data_sources) == 2
