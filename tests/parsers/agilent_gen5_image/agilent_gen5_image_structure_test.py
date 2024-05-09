import pytest

# ReadData,
from allotropy.parsers.agilent_gen5_image.agilent_gen5_image_structure import (
    HeaderData,
    LayoutData,
)
from allotropy.parsers.lines_reader import LinesReader


@pytest.mark.short
def test_create_header_data_no_well_plate_id_in_filename() -> None:
    header_rows = [
        "Software Version	3.12.08",
        "",
        "",
        "Experiment File Path:	Experiments/Imaging and Analysis Sample File.xpt",
        "Protocol File Path:	Protocols/Trevigen 96-Well Comet Slide Imaging.prt",
        "",
        "Plate Number	Plate 1",
        "Date	10/10/2022",
        "Time	6:26:57 AM",
        "Reader Type:	Cytation5",
        "Reader Serial Number:	EM-18",
        "Reading Type	Reader",
    ]
    reader = LinesReader(header_rows)
    header_data = HeaderData.create(reader, "dummy_filename.txt")

    assert header_data == HeaderData(
        software_version="3.12.08",
        experiment_file_path="Experiments/Imaging and Analysis Sample File.xpt",
        protocol_file_path="Protocols/Trevigen 96-Well Comet Slide Imaging.prt",
        datetime="10/10/2022 6:26:57 AM",
        well_plate_identifier="Plate 1",
        model_number="Cytation5",
        equipment_serial_number="EM-18",
    )


@pytest.mark.short
def test_create_header_data_with_well_plate_id_from_filename() -> None:
    header_rows = [
        "Software Version	3.12.08",
        "Experiment File Path:	Experiments/singlePlate.xpt",
        "Protocol File Path:	Protocols/defaultExport.prt",
        "Plate Number	Plate 1",
        "Date	10/10/2022",
        "Time	6:26:57 AM",
        "Reader Type:	Cytation5",
        "Reader Serial Number:	EM-18",
        "Reading Type	Reader",
    ]
    well_plate_id = "PLATEID123"
    matching_file_name = f"010307_114129_{well_plate_id}_std_01.txt"

    reader = LinesReader(header_rows)
    header_data = HeaderData.create(reader, matching_file_name)

    assert header_data.well_plate_identifier == well_plate_id


@pytest.mark.short
def test_create_layout_data() -> None:
    layout_rows = [
        "Layout",
        "\t1\t2\t3",
        "A\tSPL1\tSPL9\tSPL17\tWell ID",
        "B\tSPL2\tSPL10\tSPL18\tWell ID",
    ]

    layout_data = LayoutData.create("\n".join(layout_rows))

    assert layout_data.sample_identifiers == {
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
        "\tName_A1\tName_A2\tName_A3\tName",
        "B\tSPL2\tSPL10\tSPL18\tWell ID",
        "\tName_B1\tName_B2\tName_B3\tName",
    ]

    layout_data = LayoutData.create("\n".join(layout_rows))

    assert layout_data.sample_identifiers == {
        "A1": "Name_A1",
        "A2": "Name_A2",
        "A3": "Name_A3",
        "B1": "Name_B1",
        "B2": "Name_B2",
        "B3": "Name_B3",
    }
