from io import StringIO

import pytest

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    BasicAssayInfo,
    create_plate_maps,
    Filter,
    Instrument,
    Labels,
    Plate,
    PlateInfo,
    PlateMap,
    PlateType,
    Result,
)


def get_reader_from_lines(lines: list[str]) -> CsvReader:
    return CsvReader(StringIO("\n".join(lines)))


def test_create_plate_info() -> None:
    reader = get_reader_from_lines(
        [
            "Plate information",
            "Plate,Repeat,Barcode,Measured height,Chamber temperature at start,Measinfo,Kinetics,Measurement date,",
            '1,1,"=""BAR_123""",11.9,23.17,De=1st Ex=Top Em=Top Wdw=1 (14),0,10/13/2022 3:08:06 PM,',
        ]
    )

    expected = PlateInfo(
        number="1",
        barcode="BAR_123",
        emission_filter_id="1st",
        measurement_time="10/13/2022 3:08:06 PM",
        measured_height=11.9,
        chamber_temperature_at_start=23.17,
    )

    assert PlateInfo.create(reader) == expected


def test_create_plate_info_default_barcode() -> None:
    reader = get_reader_from_lines(
        [
            "Plate information",
            "Plate,Repeat,Barcode,Measured height,Chamber temperature at start,Measinfo,Kinetics,Measurement date,",
            '1,1,"=""""",11.9,23.17,De=1st Ex=Top Em=Top Wdw=1 (14),0,10/13/2022 3:08:06 PM,',
        ]
    )
    plate = PlateInfo.create(reader)
    assert plate and plate.barcode == "Plate 1"
    reader = get_reader_from_lines(
        [
            "Plate information",
            "Plate,Repeat,Barcode,Measured height,Chamber temperature at start,Measinfo,Kinetics,Measurement date,",
            "1,1,,11.9,23.17,De=1st Ex=Top Em=Top Wdw=1 (14),0,10/13/2022 3:08:06 PM,",
        ]
    )
    plate = PlateInfo.create(reader)
    assert plate and plate.barcode == "Plate 1"


def test_create_result() -> None:
    reader = get_reader_from_lines(
        [
            "Results",
            "1,2,,",
            "3,4,,",
            ",,,",
            "",
        ]
    )

    expected = [
        Result(col="A", row="01", value=1),
        Result(col="A", row="02", value=2),
        Result(col="B", row="01", value=3),
        Result(col="B", row="02", value=4),
    ]
    assert Result.create(reader) == expected

    # After no more results, return empty list.
    assert Result.create(reader) == []


def test_create_result_early_return() -> None:
    reader = get_reader_from_lines(
        [
            "Plate information",
            "1,2,,",
            "3,4,,",
        ]
    )
    assert Result.create(reader) == []


def test_create_plates() -> None:
    reader = get_reader_from_lines(
        [
            "Plate information",
            "Plate,Repeat,Barcode,Measured height,Chamber temperature at start,Measinfo,Kinetics,Measurement date,",
            "2,1,,1.1,14.5,De=2nd Ex=Top Em=Top Wdw=1 (14),0,10/13/2022 3:08:06 PM,",
            "",
            "Background information",
            "junk",
            "",
            "Calculated results",
            "junk",
            "",
            "Results",
            "6,,7,",
            ",,,",
            ",8,,",
        ]
    )

    expected = [
        Plate(
            plate_info=PlateInfo(
                number="2",
                barcode="Plate 2",
                emission_filter_id="2nd",
                measurement_time="10/13/2022 3:08:06 PM",
                measured_height=1.1,
                chamber_temperature_at_start=14.5,
            ),
            results=[
                Result(col="A", row="01", value=6),
                Result(col="A", row="03", value=7),
                Result(col="C", row="02", value=8),
            ],
        )
    ]

    assert Plate.create(reader) == expected


def test_create_basic_assay_info() -> None:
    reader = get_reader_from_lines(
        [
            "Basic assay information",
            "Assay ID: ,,,,3134",
            "Assay Started: ,,,,10/13/2022 3:06:23 PM",
            "Assay Finished: ,,,,10/13/2022 3:08:15 PM",
            "Assay Exported: ,,,,10/13/2022 3:08:15 PM",
            "Protocol ID: ,,,,100302",
            "Protocol Name: ,,,,HTRF LASER Eu 665/620",
            "Serial#: ,,,,='1050209'",
        ]
    )

    expected = BasicAssayInfo(
        protocol_id="100302",
        assay_id="3134",
    )

    assert BasicAssayInfo.create(reader) == expected


def test_create_basic_assay_info_fails() -> None:
    reader = get_reader_from_lines([])
    # TODO(brian): Improve src to throw AllotropeConversionError (or AllotropyError?)
    with pytest.raises(
        Exception, match="Expected non-null value for Basic assay information"
    ):
        BasicAssayInfo.create(reader)


def test_create_plate_type() -> None:
    reader = get_reader_from_lines(
        [
            "Protocol information",
            "Protocol:",
            "Protocol name,,,,protocol",
            "property,,,,1",
            "",
            "Plate type:",
            "Name of the plate type,,,,plate",
            "Number of the wells in the plate,,,,2",
        ]
    )

    expected = PlateType(number_of_wells=2)

    assert PlateType.create(reader) == expected


def test_create_plate_maps() -> None:
    reader = get_reader_from_lines(
        [
            "Platemap:",
            "Plate,,,,1",
            "Group,,,,1",
            "",
            ",01,02,03",
            "A,- ,'',",
            "B,nan,LH01,",
            "C,STD,,S01",
            "",
            "- - Undefined",
            "",
            "",
            "",
            "Plate,,,,2",
            "Group,,,,3",
            "",
            ",01,02,03,04",
            "A,,'',,BL...",
            "B,nan,nan,,",
            "C,,,,",
            "",
            "- - Undefined",
            "",
        ]
    )

    expected = {
        "1": PlateMap(
            plate_n="1",
            group_n="1",
            sample_role_type_mapping={
                "01": {
                    "A": SampleRoleType.unknown_sample_role,
                    "C": SampleRoleType.standard_sample_role,
                },
                "02": {"B": SampleRoleType.control_sample_role},
                "03": {"C": SampleRoleType.sample_role},
            },
        ),
        "2": PlateMap(
            plate_n="2",
            group_n="3",
            sample_role_type_mapping={
                "04": {"A": SampleRoleType.blank_role},
            },
        ),
    }

    assert create_plate_maps(reader) == expected


def test_create_labels() -> None:
    reader = get_reader_from_lines(
        [
            "Labels",
            "FAKE_INSTRUMENT,,,,4000013",
            "Exc. filter,,,,Filter_1",
            "Using of excitation filter,,,,Top",
            "2nd exc. filter,,,,N/A",
            "Ems. filter,,,,Filter_2",
            "2nd ems. filter,,,,N/A",
            "Measurement height,,,,5 mm",
            "Using of emission filter,,,,Top",
            "Number of flashes,,,,10",
            "Number of flashes integrated,,,,1",
            "Reference AD gain,,,,2",
            "Last edited,,,,4/6/2022 5:55:00 PM",
            "Factory preset,,,,No",
            "",
            "",
            "Filters:",
            "Filter_1,,,,102",
            "Description,,,,X485 CWL=485nm BW=14nm Tmin=60%",
            "Factory preset,,,,Yes",
            "",
            "",
            "Filter_2,,,,102",
            "Description,,,,X485 CWL=520nm BW=20nm Tmin=60%",
            "Factory preset,,,,Yes",
        ]
    )

    expected = Labels(
        label="FAKE_INSTRUMENT",
        excitation_filter=Filter(
            name="Filter_1",
            wavelength=485,
            bandwidth=14,
        ),
        emission_filters={
            "1st": Filter(
                name="Filter_2",
                wavelength=520,
                bandwidth=20,
            ),
            "2nd": None,
        },
        scan_position_setting=ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
        number_of_flashes=10.0,
        detector_gain_setting="2",
    )

    assert Labels.create(reader) == expected


def test_create_instrument() -> None:
    reader = get_reader_from_lines(
        [
            "Instrument:",
            "Serial number,,,,1",
            "Nickname,,,,bobby",
        ]
    )

    expected = Instrument(
        serial_number="1",
        nickname="bobby",
    )

    assert Instrument.create(reader) == expected
