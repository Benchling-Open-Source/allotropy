import pandas as pd

from allotropy.parsers.agilent_gen5.agilent_gen5_structure import (
    FilterSet,
    get_identifiers,
    HeaderData,
    ReadData,
)
from allotropy.parsers.agilent_gen5.constants import ReadMode
from allotropy.parsers.utils.pandas import SeriesData


def test_create_header_data_no_well_plate_id_in_filename() -> None:
    data = SeriesData(
        pd.Series(
            {
                "Software Version": "3.12.08",
                "Experiment File Path:": "Experiments/singlePlate.xpt",
                "Protocol File Path:": "Protocols/defaultExport.prt",
                "Plate Number": "Plate 1",
                "Date": "10/10/2022",
                "Time": "9:00:04 PM",
                "Reader Type:": "Synergy H1",
                "Reader Serial Number:": "Serial01",
                "Reading Type": "Manual",
                "Plate Type": "96 WELL PLATE (Use plate lid)",
            }
        )
    )

    header_data = HeaderData.create(data, "users/files/dummy_filename.txt")

    assert header_data == HeaderData(
        software_version="3.12.08",
        experiment_file_path="Experiments/singlePlate.xpt",
        protocol_file_path="Protocols/defaultExport.prt",
        datetime="10/10/2022 9:00:04 PM",
        well_plate_identifier="Plate 1",
        model_number="Synergy H1",
        equipment_serial_number="Serial01",
        file_name="dummy_filename.txt",
        unc_path="users/files/dummy_filename.txt",
        plate_well_count=96,
        additional_data={
            "Reading Type": "Manual",
        },
    )


def test_create_header_data_with_well_plate_id_from_filename() -> None:
    well_plate_id = "PLATEID123"
    matching_file_name = f"010307_114129_{well_plate_id}_std_01.txt"

    data = SeriesData(
        pd.Series(
            {
                "Software Version": "3.12.08",
                "Experiment File Path:": "Experiments/singlePlate.xpt",
                "Protocol File Path:": "Protocols/defaultExport.prt",
                "Date": "10/10/2022",
                "Time": "9:00:04 PM",
                "Reader Type:": "Synergy H1",
                "Reader Serial Number:": "Serial01",
                "Reading Type": "Manual",
                "Plate Type": "96 WELL PLATE (Use plate lid)",
            }
        )
    )
    header_data = HeaderData.create(data, matching_file_name)

    assert header_data.well_plate_identifier == well_plate_id


def test_create_read_data_with_step_label() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read\tStepLabel",
        "\tAbsorbance Endpoint",
    ]
    read_data = ReadData.create(absorbance_procedure_details)

    assert read_data[0].step_label == "StepLabel"


def test_create_read_data_without_step_label() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read\t",
        "\tAbsorbance Endpoint",
    ]
    read_data = ReadData.create(absorbance_procedure_details)

    assert read_data[0].step_label is None


def test_create_read_data_absorbance() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read\t260",
        "\tAbsorbance Endpoint",
        "\tFull Plate",
        "\tWavelengths:  260, 280, 230",
        "\tPathlength Correction: 977 / 900",
        "\t    Absorbance at 1 cm: 0.18",
        "\tRead Speed: Normal,  Delay: 100 msec,  Measurements/Data Point: 8",
    ]
    read_data = ReadData.create(absorbance_procedure_details)

    assert len(read_data) == 1
    assert read_data[0].read_mode == ReadMode.ABSORBANCE
    assert read_data[0].pathlength_correction == "977 / 900"
    assert read_data[0].step_label == "260"
    assert read_data[0].detector_carriage_speed == "Normal"  # Read Speed
    assert read_data[0].number_of_averages == 8  # Measurements/Data Point
    assert read_data[0].measurement_labels == {
        "260:260",
        "260:280",
        "260:230",
        "260:977 [Test]",
        "260:900 [Ref]",
    }


def test_create_read_data_luminescence_full_light() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read\tLUM",
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
    read_data = ReadData.create(absorbance_procedure_details)

    assert len(read_data) == 1
    assert read_data[0].read_mode == ReadMode.LUMINESCENCE
    assert read_data[0].step_label == "LUM"
    assert read_data[0].detector_carriage_speed == "Normal"  # Read Speed
    assert read_data[0].detector_distance == 4.5  # Read Height
    assert read_data[0].measurement_labels == {"LUM:Lum"}
    assert read_data[0].filter_sets == {
        "LUM:Lum": FilterSet(emission="Full light", gain="135", optics="Top")
    }


def test_create_read_data_luminescence_text_settings() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read\t",
        "\tLuminescence Endpoint",
        "\tFull Plate",
        "\tIntegration Time: 0:01.00 (MM:SS.ss)",
        "\tFilter Set 1",
        "\t    Excitation: Plug,  Emission: Hole",
        "\t    Optics: Top,  Gain: 135",
        "\tRead Speed: Normal,  Delay: 100 msec",
        "\tExtended Dynamic Range",
        "\tRead Height: 4.5 mm",
    ]
    read_data = ReadData.create(absorbance_procedure_details)

    assert len(read_data) == 1
    assert read_data[0].read_mode == ReadMode.LUMINESCENCE
    assert read_data[0].detector_carriage_speed == "Normal"  # Read Speed
    assert read_data[0].detector_distance == 4.5  # Read Height
    assert read_data[0].measurement_labels == {"Lum"}
    assert read_data[0].filter_sets == {
        "Lum": FilterSet(emission="Hole", gain="135", optics="Top", excitation="Plug")
    }


def test_create_read_data_luminescence_with_filter() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read\tLUM",
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
    read_data = ReadData.create(absorbance_procedure_details)

    assert len(read_data) == 1
    assert read_data[0].read_mode == ReadMode.LUMINESCENCE
    assert read_data[0].step_label == "LUM"
    assert read_data[0].detector_carriage_speed == "Normal"  # Read Speed
    assert read_data[0].detector_distance == 4.5  # Read Height
    assert read_data[0].measurement_labels == {"LUM:460/40"}
    assert read_data[0].filter_sets == {
        "LUM:460/40": FilterSet(emission="460/40", gain="136")
    }


def test_create_read_data_fluorescence() -> None:
    absorbance_procedure_details = [
        "Procedure Details",
        "Read\tDAPI/GFP",
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
    read_data = ReadData.create(absorbance_procedure_details)

    assert len(read_data) == 1
    assert read_data[0].read_mode == ReadMode.FLUORESCENCE
    assert read_data[0].step_label == "DAPI/GFP"
    assert read_data[0].detector_carriage_speed == "Normal"  # Read Speed
    assert read_data[0].detector_distance == 7  # Read Height
    assert read_data[0].number_of_averages == 10  # Measurements/Data Point
    assert read_data[0].measurement_labels == {
        "DAPI/GFP:360/40,460/40",
        "DAPI/GFP:485/20,528/20",
        "DAPI/GFP:360,460",
        "DAPI/GFP:485,528",
    }
    assert read_data[0].filter_sets == {
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
        "DAPI/GFP:485,528": FilterSet(
            excitation="485/20",
            emission="528/20",
            optics=None,
            mirror="Top 510 nm",
            gain="35",
        ),
        "DAPI/GFP:360,460": FilterSet(
            excitation="360/40",
            emission="460/40",
            optics=None,
            mirror="Top 400 nm",
            gain="35",
        ),
    }


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


def test_create_filter_set_full_light() -> None:
    filterset = FilterSet(emission="Full light", gain="135", optics="Top")

    assert filterset.detector_wavelength_setting is None
    assert filterset.detector_bandwidth_setting is None
    assert filterset.excitation_wavelength_setting is None
    assert filterset.excitation_bandwidth_setting is None
    assert filterset.gain == "135"


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


def test_create_multiple_read_modes() -> None:
    multiple_read_modes = [
        "Procedure Details",
        "Plate Type\t96 WELL PLATE (Use plate lid)",
        "Read\tod",
        "\tAbsorbance Endpoint",
        "\tFull Plate",
        "\tWavelengths:  600",
        "\tRead Speed: Normal,  Delay: 100 msec,  Measurements/Data Point: 8",
        "Read\tfluor",
        "\tFluorescence Endpoint",
        "\tFull Plate",
        "\tFilter Set 1",
        "\t\tExcitation: 579,  Emission: 616",
        "\t\tOptics: Top,  Gain: extended",
        "\tFilter Set 2",
        "\t\tExcitation: 479,  Emission: 520",
        "\t\tOptics: Top,  Gain: extended",
    ]

    read_data = ReadData.create(multiple_read_modes)

    assert len(read_data) == 2
    assert read_data[0].read_mode == ReadMode.ABSORBANCE
    assert read_data[0].step_label == "od"
    assert read_data[0].measurement_labels == {"od:600"}
    assert read_data[0].number_of_averages == 8
    assert read_data[0].detector_carriage_speed == "Normal"

    assert read_data[1].read_mode == ReadMode.FLUORESCENCE
    assert read_data[1].step_label == "fluor"
    assert read_data[1].filter_sets == {
        "fluor:579,616": FilterSet(
            excitation="579",
            emission="616",
            optics="Top",
            gain="extended",
        ),
        "fluor:479,520": FilterSet(
            excitation="479",
            emission="520",
            optics="Top",
            gain="extended",
        ),
    }


def test_create_three_read_modes() -> None:
    multiple_read_modes = [
        "Procedure Details",
        "Plate Type\t96 WELL PLATE (Use plate lid)",
        "Read\tod",
        "\tAbsorbance Endpoint",
        "\tFull Plate",
        "\tWavelengths:  600",
        "\tRead Speed: Normal,  Delay: 100 msec,  Measurements/Data Point: 8",
        "Read\tfluor",
        "\tFluorescence Endpoint",
        "\tFull Plate",
        "\tFilter Set 1",
        "\t\tExcitation: 579,  Emission: 616",
        "\t\tOptics: Top,  Gain: extended",
        "\tFilter Set 2",
        "\t\tExcitation: 479,  Emission: 520",
        "\t\tOptics: Top,  Gain: extended",
        "Read\tLUM",
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

    read_data = ReadData.create(multiple_read_modes)

    assert len(read_data) == 3
    assert read_data[0].read_mode == ReadMode.ABSORBANCE
    assert read_data[0].step_label == "od"
    assert read_data[0].measurement_labels == {"od:600"}
    assert read_data[0].number_of_averages == 8
    assert read_data[0].detector_carriage_speed == "Normal"

    assert read_data[1].read_mode == ReadMode.FLUORESCENCE
    assert read_data[1].step_label == "fluor"
    assert read_data[1].filter_sets == {
        "fluor:579,616": FilterSet(
            excitation="579",
            emission="616",
            optics="Top",
            gain="extended",
        ),
        "fluor:479,520": FilterSet(
            excitation="479",
            emission="520",
            optics="Top",
            gain="extended",
        ),
    }

    assert read_data[2].read_mode == ReadMode.LUMINESCENCE
    assert read_data[2].step_label == "LUM"
    assert read_data[2].measurement_labels == {"LUM:460/40"}
    assert read_data[2].filter_sets == {
        "LUM:460/40": FilterSet(
            emission="460/40",
            gain="136",
        )
    }
    assert read_data[2].detector_carriage_speed == "Normal"
    assert read_data[2].detector_distance == 4.5


def test_create_two_same_read_modes() -> None:
    multiple_read_modes = [
        "Procedure Details",
        "Plate Type\t96 WELL PLATE (Use plate lid)",
        "Read\tod",
        "\tAbsorbance Endpoint",
        "\tFull Plate",
        "\tWavelengths:  600",
        "\tRead Speed: Normal,  Delay: 100 msec,  Measurements/Data Point: 8",
        "Read\t260",
        "\tAbsorbance Endpoint",
        "\tFull Plate",
        "\tWavelengths:  260, 280, 230",
        "\tPathlength Correction: 977 / 900",
        "\t    Absorbance at 1 cm: 0.18",
        "\tRead Speed: Normal,  Delay: 100 msec,  Measurements/Data Point: 8",
    ]

    read_data = ReadData.create(multiple_read_modes)

    assert len(read_data) == 2
    assert read_data[0].read_mode == ReadMode.ABSORBANCE
    assert read_data[0].step_label == "od"
    assert read_data[0].measurement_labels == {"od:600"}
    assert read_data[0].number_of_averages == 8
    assert read_data[0].detector_carriage_speed == "Normal"

    assert read_data[1].read_mode == ReadMode.ABSORBANCE
    assert read_data[1].step_label == "260"
    assert read_data[1].detector_carriage_speed == "Normal"
    assert read_data[1].measurement_labels == {
        "260:260",
        "260:280",
        "260:230",
        "260:977 [Test]",
        "260:900 [Ref]",
    }
    assert read_data[1].number_of_averages == 8
    assert read_data[1].pathlength_correction == "977 / 900"


def test_create_two_same_read_modes_from_file() -> None:
    file_path = (
        "tests/parsers/agilent_gen5/testdata/multi_read_modes/two_same_read_modes.txt"
    )

    with open(file_path) as f:
        file_contents = f.readlines()

    read_data = ReadData.create(file_contents)

    assert len(read_data) == 2
    assert read_data[0].read_mode == ReadMode.ABSORBANCE
    assert read_data[0].step_label == "od"
    assert read_data[0].measurement_labels == {"od:600"}
    assert read_data[0].number_of_averages == 8
    assert read_data[0].detector_carriage_speed == "Normal"

    assert read_data[1].read_mode == ReadMode.ABSORBANCE
    assert read_data[1].step_label == "260"
    assert read_data[1].detector_carriage_speed == "Normal"
    assert read_data[1].measurement_labels == {
        "260:280",
        "260:977 [Test]",
        "260:900 [Ref]",
    }
    assert read_data[1].number_of_averages == 8
    assert read_data[1].pathlength_correction == "977 / 900"


def test_create_two_read_modes_from_file() -> None:
    file_path = (
        "tests/parsers/agilent_gen5/testdata/multi_read_modes/multiple_read_modes.txt"
    )

    with open(file_path) as f:
        file_contents = f.readlines()

    read_data = ReadData.create(file_contents)

    assert len(read_data) == 2
    assert read_data[0].read_mode == ReadMode.ABSORBANCE
    assert read_data[0].step_label == "od"
    assert read_data[0].measurement_labels == {"od:600"}
    assert read_data[0].number_of_averages == 8
    assert read_data[0].detector_carriage_speed == "Normal"

    assert read_data[1].read_mode == ReadMode.FLUORESCENCE
    assert read_data[1].step_label == "fluor"
    assert read_data[1].filter_sets == {
        "fluor:579,616": FilterSet(
            excitation="579",
            emission="616",
            optics="Top",
            gain="extended",
        ),
        "fluor:479,520": FilterSet(
            excitation="479",
            emission="520",
            optics="Top",
            gain="extended",
        ),
    }
