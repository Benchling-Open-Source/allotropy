from io import StringIO
from unittest.mock import MagicMock, patch

import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.bmg_labtech_smart_control.bmg_labtech_smart_control_reader import (
    BmgLabtechSmartControlReader,
    SheetNames,
)


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

    assert reader.header[str, "User"] == "user"
    assert reader.header[str, "Test ID"] == "9"
    assert reader.header[str, "ID3"] == "Plate 3"
    assert reader.header[str, "Measurement type"] == "Fluorescence (FI)"
    assert reader.header[str, "Excitation"] == "480-14"
    assert reader.header[str, "Focal height  [mm]"] == "5.9"
    assert (
        reader.header[str, "Reading direction"]
        == "bidirectional, horizontal left to right, top to bottom"
    )
    assert reader.header[str, "Target temperature [°C]"] == "set off"
    assert reader.header[str, "Target concentration O2 [%]"] == "set off"
    assert reader.header[str, "Target concentration CO2 [%]"] == "set off"
    assert reader.data.shape == (8, 6)
