import pytest

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    TransmittedLightSetting,
)
from allotropy.parsers.agilent_gen5_image.agilent_gen5_image_structure import (
    HeaderData,
    InstrumentSettings,
    LayoutData,
    ReadData,
    ReadSection,
)
from allotropy.parsers.agilent_gen5_image.constants import DetectionType
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


@pytest.mark.short
def test_create_read_data() -> None:
    procedure_details = [
        "Procedure Details",
        "",
        "Eject plate on completion	",
        "Read\t2.5x Imaging",
        "\tImage Single Image",
        "\tFull Plate",
        "\tObjective: 2.74x",
        "\tChannel 1:  GFP 469,525",
        "\t    LED intensity: 5, Integration time: 110 msec, Camera gain: 0",
        "\t    Autofocus with optional scan",
        "\t    Images to average: 1",
        "\tHorizontal offset: 0 µm, Vertical offset: 0 µm",
        "Read\t4x Montage Imaging",
        "\tImage Montage",
        "\tFull Plate",
        "\tObjective: 4x",
        "\tChannel 1:  GFP 469,525",
        "\t    LED intensity: 9, Integration time: 100 msec, Camera gain: 1",
        "\t    Autofocus with optional scan",
        "\t    Images to average: 1",
        "\tHorizontal offset: 0 µm, Vertical offset: 0 µm",
        "\tMontage rows: 2, columns: 2",
    ]
    reader = LinesReader(procedure_details)
    read_data = ReadData.create(reader=reader)

    assert len(read_data.read_sections) == 2
    assert read_data.read_sections[0].image_mode == DetectionType.SINGLE_IMAGE
    assert read_data.read_sections[1].image_mode == DetectionType.MONTAGE
    assert read_data.read_sections[0].magnification_setting == 2.74
    assert read_data.read_sections[1].magnification_setting == 4


@pytest.mark.short
def test_create_read_section_channel_settings() -> None:
    read_section_lines = [
        "Read\tImage Single Image",
        "\tFull Plate",
        "\tObjective: 20x",
        "\tField of View: Standard",
        "\tChannel 1:  Phase Contrast",
        "\t    LED intensity: 10, Integration time: 144 msec, Camera gain: 15.6",
        "\t    Laser autofocus",
        "\t    Scan distance: 600 µm",
        "\t    Scan increment: 7 µm",
        "\t    Offset from bottom of well: 0 µm",
        "\t    Vibration CV threshold: 0.01",
        "\t    Images to average: 1",
        "\tChannel 2:  YFP 500,542",
        "\t    LED intensity: 11, Integration time: 303 msec, Camera gain: 20",
        "\t    Use focal height from first channel with offset of -5 µm",
        "\t    Vibration CV threshold: 0.01",
        "\t    Images to average: 1",
        "\tChannel 3:  Texas Red 586,647",
        "\t    LED intensity: 9, Integration time: 405 msec, Camera gain: 20",
        "\t    Use focal height from first channel with offset of 0 µm",
        "\t    Vibration CV threshold: 0.01",
        "\t    Images to average: 1",
        "\tHorizontal offset: -3000 µm, Vertical offset: -142 µm",
        "\tDelay after plate movement: 300 msec",
    ]
    reader = LinesReader(read_section_lines)
    read_section = ReadSection.create(reader)

    assert read_section == ReadSection(
        image_mode=DetectionType.SINGLE_IMAGE,
        magnification_setting=20,
        image_count_setting=None,
        instrument_settings_list=[
            InstrumentSettings(
                auto_focus=True,
                detector_distance=None,
                detector_gain="15.6",
                exposure_duration=144,
                illumination=10,
            ),
            InstrumentSettings(
                auto_focus=True,
                detector_distance=None,
                fluorescent_tag="YFP",
                excitation_wavelength=500,
                detector_wavelength=542,
                detector_gain="20",
                exposure_duration=303,
                illumination=11,
            ),
            InstrumentSettings(
                auto_focus=True,
                detector_distance=None,
                fluorescent_tag="Texas Red",
                excitation_wavelength=586,
                detector_wavelength=647,
                detector_gain="20",
                exposure_duration=405,
                illumination=9,
            ),
        ],
    )


@pytest.mark.short
@pytest.mark.parametrize(
    ("rows", "columns", "count"),
    ((2, 4, 8), (3, 5, 15), (5, 6, 30)),
)
def test_create_read_section_image_montage_count(
    rows: int, columns: int, count: int
) -> None:
    read_section_lines = [
        "Read	4x Montage Imaging",
        "\tImage Montage",
        "\tFull Plate",
        "\tObjective: 4x",
        "\tField of View: Standard",
        "\tChannel 1:  GFP 469,525",
        "\t    LED intensity: 9, Integration time: 100 msec, Camera gain: 1",
        "\t    Autofocus with optional scan",
        "\t    Offset from bottom of well: 0 µm",
        "\t    Vibration CV threshold: 0.01",
        "\t    Images to average: 1",
        "\tHorizontal offset: 0 µm, Vertical offset: 0 µm",
        f"\tMontage rows: {rows}, columns: {columns}",
        "\tMontage horizontal spacing: 1776 µm, vertical spacing: 1311 µm",
        "\tMontage autofocus option: Autofocus option based on objective size",
    ]
    reader = LinesReader(read_section_lines)
    read_section = ReadSection.create(reader)

    assert read_section.image_mode == DetectionType.MONTAGE
    assert read_section.image_count_setting == count


@pytest.mark.short
@pytest.mark.parametrize("detector_distance", (-450, 0, 1200, -445.7))
def test_create_instrument_settings_detector_distance(detector_distance: float) -> None:
    settings_lines = [
        "\tColor Camera",
        "\t    Transmitted light",
        "\t    LED intensity: 1, Integration time: 5 msec, Camera gain: 5",
        f"\t    Fixed focal height at bottom elevation plus {detector_distance} mm",
        "\t    Vibration CV threshold: 0.01",
        "\t    Images to average: 1",
    ]
    instrument_settings = InstrumentSettings.create(settings_lines)

    assert instrument_settings.auto_focus is False
    assert instrument_settings.detector_distance == detector_distance


@pytest.mark.short
@pytest.mark.parametrize(
    ("transmitted_light", "expected"),
    (
        (
            ("Brightfield", TransmittedLightSetting.brightfield),
            ("Phase Contrast", TransmittedLightSetting.phase_contrast),
            ("Transmitted Light", TransmittedLightSetting.brightfield),
            ("Reflected Light", TransmittedLightSetting.brightfield),
            ("Color Bright Field", TransmittedLightSetting.brightfield),
        )
    ),
)
@pytest.mark.short
def test_create_instrument_settings_transmitted_light_correct_mapping(
    transmitted_light: str, expected: TransmittedLightSetting
) -> None:
    settings_lines = [
        "\tColor Camera",
        f"\t    {transmitted_light}",
        "\t    LED intensity: 1, Integration time: 5 msec, Camera gain: 5",
        "\t    Fixed focal height at bottom elevation plus 40 mm",
        "\t    Vibration CV threshold: 0.01",
        "\t    Images to average: 1",
    ]
    instrument_settings = InstrumentSettings.create(settings_lines)

    assert instrument_settings.transmitted_light == expected
