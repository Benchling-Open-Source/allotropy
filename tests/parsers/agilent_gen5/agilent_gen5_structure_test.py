import pytest

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.definitions.definitions import InvalidJsonFloat
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import (
    FilterSet,
    get_identifiers,
    HeaderData,
    ReadData,
)
from allotropy.parsers.agilent_gen5.constants import ReadMode
from allotropy.parsers.lines_reader import LinesReader


@pytest.mark.short
def test_create_header_data_no_well_plate_id_in_filename() -> None:
    header_rows = [
        "Software Version	3.12.08",
        "",
        "",
        "Experiment File Path:	Experiments/singlePlate.xpt",
        "Protocol File Path:	Protocols/defaultExport.prt",
        "",
        "Plate Number	Plate 1",
        "Date	10/10/2022",
        "Time	9:00:04 PM",
        "Reader Type:	Synergy H1",
        "Reader Serial Number:	Serial01",
        "Reading Type	Manual",
    ]
    reader = LinesReader(header_rows)
    header_data = HeaderData.create(reader, "dummy_filename.txt")

    assert header_data == HeaderData(
        software_version="3.12.08",
        experiment_file_path="Experiments/singlePlate.xpt",
        protocol_file_path="Protocols/defaultExport.prt",
        datetime="10/10/2022 9:00:04 PM",
        well_plate_identifier="Plate 1",
        model_number="Synergy H1",
        equipment_serial_number="Serial01",
        file_name="dummy_filename.txt",
    )


@pytest.mark.short
def test_create_header_data_with_well_plate_id_from_filename() -> None:
    header_rows = [
        "Software Version	3.12.08",
        "Experiment File Path:	Experiments/singlePlate.xpt",
        "Protocol File Path:	Protocols/defaultExport.prt",
        "Plate Number	Plate 1",
        "Date	10/10/2022",
        "Time	9:00:04 PM",
        "Reader Type:	Synergy H1",
        "Reader Serial Number:	Serial01",
        "Reading Type	Manual",
    ]
    well_plate_id = "PLATEID123"
    matching_file_name = f"010307_114129_{well_plate_id}_std_01.txt"

    reader = LinesReader(header_rows)
    header_data = HeaderData.create(reader, matching_file_name)

    assert header_data.well_plate_identifier == well_plate_id


@pytest.mark.short
def test_create_read_data_with_step_label() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read	StepLabel",
        "\tAbsorbance Endpoint",
    ]
    reader = LinesReader(absorbance_procedure_details)

    read_data = ReadData.create(reader)

    assert read_data.step_label == "StepLabel"


@pytest.mark.short
def test_create_read_data_without_step_label() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read	Absorbance Endpoint",
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
    assert read_data.pathlength_correction == "977 / 900"
    assert read_data.step_label == "260"
    assert read_data.detector_carriage_speed == "Normal"  # Read Speed
    assert read_data.number_of_averages == 8  # Measurements/Data Point
    assert read_data.measurement_labels == {
        "260:260",
        "260:280",
        "260:230",
        "260:977 [Test]",
        "260:900 [Ref]",
    }


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
    assert read_data.detector_distance == 4.5  # Read Height
    assert read_data.measurement_labels == {"LUM:Lum"}
    assert read_data.filter_sets == {
        "LUM:Lum": FilterSet(emission="Full light", gain="135", optics="Top")
    }


@pytest.mark.short
def test_create_read_data_luminescence_text_settings() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read	Luminescence Endpoint",
        "\tFull Plate",
        "\tIntegration Time: 0:01.00 (MM:SS.ss)",
        "\tFilter Set 1",
        "\t    Excitation: Plug,  Emission: Hole",
        "\t    Optics: Top,  Gain: 135",
        "\tRead Speed: Normal,  Delay: 100 msec",
        "\tExtended Dynamic Range",
        "\tRead Height: 4.5 mm",
    ]
    reader = LinesReader(absorbance_procedure_details)

    read_data = ReadData.create(reader)

    assert read_data.read_mode == ReadMode.LUMINESCENCE
    assert read_data.detector_carriage_speed == "Normal"  # Read Speed
    assert read_data.detector_distance == 4.5  # Read Height
    assert read_data.measurement_labels == {"Lum"}
    assert read_data.filter_sets == {
        "Lum": FilterSet(emission="Hole", gain="135", optics="Top", excitation="Plug")
    }


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
    assert read_data.detector_distance == 4.5  # Read Height
    assert read_data.measurement_labels == {"LUM:460/40"}
    assert read_data.filter_sets == {
        "LUM:460/40": FilterSet(emission="460/40", gain="136")
    }


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
    assert read_data.detector_distance == 7  # Read Height
    assert read_data.number_of_averages == 10  # Measurements/Data Point
    assert read_data.measurement_labels == {
        "DAPI/GFP:360/40,460/40",
        "DAPI/GFP:485/20,528/20",
        "DAPI/GFP:360,460",
        "DAPI/GFP:485,528",
    }
    assert read_data.filter_sets == {
        "DAPI/GFP:360/40,460/40": FilterSet(
            excitation="360/40",
            emission="460/40",
            mirror="Top 400 nm",
            gain="35",
        ),
        "DAPI/GFP:485/20,528/20": FilterSet(
            excitation="485/20",
            emission="528/20",
            mirror="Top 510 nm",
            gain="35",
        ),
        "DAPI/GFP:360,460": FilterSet(
            excitation="360/40",
            emission="460/40",
            mirror="Top 400 nm",
            gain="35",
        ),
        "DAPI/GFP:485,528": FilterSet(
            excitation="485/20",
            emission="528/20",
            mirror="Top 510 nm",
            gain="35",
        ),
    }


@pytest.mark.short
def test_create_filter_set() -> None:
    filterset = FilterSet(
        excitation="485/20",
        emission="528/20",
        mirror="Top 510 nm",
        gain="35",
    )

    assert filterset.detector_wavelength_setting == 528
    assert filterset.detector_bandwidth_setting == 20
    assert filterset.excitation_wavelength_setting == 485
    assert filterset.excitation_bandwidth_setting == 20
    assert filterset.wavelength_filter_cutoff_setting == 510
    assert (
        filterset.scan_position_setting
        == ScanPositionSettingPlateReader.top_scan_position__plate_reader_
    )


@pytest.mark.short
def test_create_filter_set_with_mirror() -> None:
    filterset = FilterSet(
        excitation="485",
        emission="528",
        optics="Bottom",
        gain="35",
    )

    assert filterset.detector_wavelength_setting == 528
    assert filterset.detector_bandwidth_setting is None
    assert filterset.excitation_wavelength_setting == 485
    assert filterset.excitation_bandwidth_setting is None
    assert filterset.wavelength_filter_cutoff_setting is None
    assert (
        filterset.scan_position_setting
        == ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_
    )


@pytest.mark.short
def test_create_filter_set_full_light() -> None:
    filterset = FilterSet(emission="Full light", gain="135", optics="Top")

    assert filterset.detector_wavelength_setting == InvalidJsonFloat.NaN
    assert filterset.detector_bandwidth_setting is None
    assert filterset.excitation_wavelength_setting is None
    assert filterset.excitation_bandwidth_setting is None
    assert filterset.gain == "135"
    assert (
        filterset.scan_position_setting
        == ScanPositionSettingPlateReader.top_scan_position__plate_reader_
    )


@pytest.mark.short
def test_create_layout_data() -> None:
    layout_rows = [
        "Layout",
        "\t1\t2\t3",
        "A\tSPL1\tSPL9\tSPL17\tWell ID",
        "B\tSPL2\tSPL10\tSPL18\tWell ID",
    ]

    sample_identifiers = get_identifiers(layout_rows)

    assert sample_identifiers == {
        "A1": "SPL1",
        "A2": "SPL9",
        "A3": "SPL17",
        "B1": "SPL2",
        "B2": "SPL10",
        "B3": "SPL18",
    }


@pytest.mark.short
def test_create_layout_data_with_name_rows() -> None:
    layout_rows = [
        "Layout",
        "\t1\t2\t3",
        "A\tSPL1\tSPL9\tSPL17\tWell ID",
        "\tName_A1\t\tName_A3\tName",
        "B\tSPL2\tSPL10\tSPL18\tWell ID",
        "\tName_B1\tName_B2\tName_B3\tName",
    ]

    sample_identifiers = get_identifiers(layout_rows)

    assert sample_identifiers == {
        "A1": "Name_A1",
        # NOTE: this tests that we fall back to Well ID if Name is not provided.
        "A2": "SPL9",
        "A3": "Name_A3",
        "B1": "Name_B1",
        "B2": "Name_B2",
        "B3": "Name_B3",
    }


@pytest.mark.short
def test_create_layout_data_with_name_rows_name_row_first() -> None:
    layout_rows = [
        "Layout",
        "\t1\t2\t3",
        "A\tName_A1\tName_A2\tName_A3\tName",
        "\tSPL1\tSPL9\tSPL17\tWell ID",
        "B\tName_B1\tName_B2\tName_B3\tName",
        "\tSPL2\tSPL10\tSPL18\tWell ID",
    ]

    sample_identifiers = get_identifiers(layout_rows)

    assert sample_identifiers == {
        "A1": "Name_A1",
        "A2": "Name_A2",
        "A3": "Name_A3",
        "B1": "Name_B1",
        "B2": "Name_B2",
        "B3": "Name_B3",
    }
