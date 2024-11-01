import pytest

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    TransmittedLightSetting,
)
from allotropy.parsers.agilent_gen5_image.agilent_gen5_image_structure import (
    InstrumentSettings,
    ReadData,
    ReadSection,
)
from allotropy.parsers.agilent_gen5_image.constants import DetectionType
from allotropy.parsers.lines_reader import LinesReader


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
    read_data = ReadData.create(procedure_details)

    assert len(read_data.read_sections) == 2
    assert read_data.read_sections[0].image_mode == DetectionType.SINGLE_IMAGE
    assert read_data.read_sections[1].image_mode == DetectionType.MONTAGE
    assert read_data.read_sections[0].magnification_setting == 2.74
    assert read_data.read_sections[1].magnification_setting == 4


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
                transmitted_light=TransmittedLightSetting.phase_contrast,
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
