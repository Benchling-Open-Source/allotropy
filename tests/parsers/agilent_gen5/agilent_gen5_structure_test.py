import pytest

from allotropy.parsers.agilent_gen5.constants import ReadMode
from allotropy.parsers.agilent_gen5.plate_data import ReadData
from allotropy.parsers.lines_reader import LinesReader


@pytest.mark.short
def test_create_read_data_with_step_label() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read	StepLabel",
        "\tLuminescence Endpoint",
    ]
    reader = LinesReader(absorbance_procedure_details)

    read_data = ReadData.create(reader)

    assert read_data.step_label == "StepLabel"


@pytest.mark.short
def test_create_read_data_without_step_label() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read	Luminescence Endpoint",
    ]
    reader = LinesReader(absorbance_procedure_details)

    read_data = ReadData.create(reader)

    assert read_data.step_label is None


@pytest.mark.short
def test_create_read_data_absorbance() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read	260",
        "\tAbsorbance Endpoint",
        "\tFull Plate",
        "\tWavelengths:  260, 280, 230",
        "\tPathlength Correction: 977 / 900",
        "\t    Absorbance at 1 cm: 0.18",
        "\tRead Speed: Normal,  Delay: 100 msec,  Measurements/Data Point: 8",
    ]
    reader = LinesReader(absorbance_procedure_details)

    read_data = ReadData.create(reader)

    assert read_data.read_mode == ReadMode.ABSORBANCE
    assert read_data.wavelengths == [260, 280, 230, 977, 900]
    assert read_data.step_label == "260"
    assert read_data.detector_carriage_speed == "Normal"  # Read Speed
    assert read_data.number_of_averages == 8  # Measurements/Data Point


@pytest.mark.short
def test_create_read_data_luminescence_full_light() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read	LUM",
        "\tLuminescence Endpoint",
        "\tFull Plate",
        "\tIntegration Time: 0:01.00 (MM:SS.ss)",
        "\tFilter Set 1",
        "\t    Emission: Full light",
        "\t    Optics: Top,  Gain: 135",
        "\tRead Speed: Normal,  Delay: 100 msec",
        "\tExtended Dynamic Range",
        "\tRead Height: 4.5 mm",
    ]
    reader = LinesReader(absorbance_procedure_details)

    read_data = ReadData.create(reader)

    assert read_data.read_mode == ReadMode.LUMINESCENCE
    assert read_data.step_label == "LUM"
    assert read_data.detector_carriage_speed == "Normal"  # Read Speed
    assert read_data.emissions == ["Full light"]
    assert read_data.optics == ["Top"]
    assert read_data.gains == [135]
    assert read_data.detector_distance == 4.5  # Read Height


@pytest.mark.short
def test_create_read_data_luminescence_with_filter() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read	LUM",
        "\tLuminescence Endpoint",
        "\tFull Plate",
        "\tIntegration Time: 0:01.00 (MM:SS.ss)",
        "\tFilter Set 2 (Blue)",
        "\t    Emission: 460/40",
        "\t    Mirror: Top 400 nm,  Gain: 136",
        "\tRead Speed: Normal,  Delay: 100 msec",
        "\tExtended Dynamic Range",
        "\tRead Height: 4.5 mm",
    ]
    reader = LinesReader(absorbance_procedure_details)

    read_data = ReadData.create(reader)

    assert read_data.read_mode == ReadMode.LUMINESCENCE
    assert read_data.step_label == "LUM"
    assert read_data.detector_carriage_speed == "Normal"  # Read Speed
    assert read_data.emissions == ["460/40"]
    assert read_data.gains == [136]
    assert read_data.detector_distance == 4.5  # Read Height


@pytest.mark.short
def test_create_read_data_fluorescence() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read	DAPI/GFP",
        "\tFluorescence Endpoint",
        "\tFull Plate",
        "\tFilter Set 1 (Blue)",
        "\t    Excitation: 360/40,  Emission: 460/40",
        "\t    Mirror: Top 400 nm,  Gain: 35",
        "\tFilter Set 2 (Green)",
        "\t    Excitation: 485/20,  Emission: 528/20",
        "\t    Mirror: Top 510 nm,  Gain: 35",
        "\tLight Source: Xenon Flash,  Lamp Energy: High",
        "\tRead Speed: Normal,  Delay: 100 msec,  Measurements/Data Point: 10",
        "\tRead Height: 7 mm",
    ]
    reader = LinesReader(absorbance_procedure_details)

    read_data = ReadData.create(reader)

    assert read_data.read_mode == ReadMode.FLUORESCENCE
    assert read_data.step_label == "DAPI/GFP"
    assert read_data.detector_carriage_speed == "Normal"  # Read Speed
    assert read_data.emissions == ["460/40", "528/20"]
    assert read_data.excitations == ["360/40", "485/20"]
    assert read_data.wavelength_filter_cut_offs == [400, 510]  # Mirror if present
    assert read_data.scan_positions == ["Top", "Top"]  # Reported by Miror or Optic
    assert read_data.gains == [35, 35]
    assert read_data.detector_distance == 7  # Read Height
    assert read_data.number_of_averages == 10  # Measurements/Data Point
