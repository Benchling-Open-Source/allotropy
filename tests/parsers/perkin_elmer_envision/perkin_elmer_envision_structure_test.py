import pandas as pd
import pytest

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    ScanPositionSettingPlateReader,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    BackgroundInfo,
    BasicAssayInfo,
    CalculatedPlate,
    CalculatedPlateInfo,
    CalculatedResult,
    create_plate_maps,
    create_results,
    Filter,
    Instrument,
    Labels,
    PlateList,
    PlateMap,
    PlateType,
    Result,
    ResultPlate,
    ResultPlateInfo,
)
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.testing.utils import mock_uuid_generation


def get_reader_from_lines(lines: list[str]) -> CsvReader:
    return CsvReader(lines)


def test_create_plate_info() -> None:
    reader = get_reader_from_lines(
        [
            "Plate information",
            "Plate,Repeat,Barcode,Measured height,Chamber temperature at start,Label,Measinfo,Kinetics,Measurement date,",
            '1,1,"=""BAR_123""",11.9,23.17,AC HTRF Laser [Eu](1),De=1st Ex=Top Em=Top Wdw=1 (14),0,10/13/2022 3:08:06 PM,',
        ]
    )

    expected = ResultPlateInfo(
        number="1",
        barcode="BAR_123",
        emission_filter_id="1st",
        measinfo="De=1st Ex=Top Em=Top Wdw=1 (14)",
        measurement_time="10/13/2022 3:08:06 PM",
        measured_height=11.9,
        chamber_temperature_at_start=23.17,
        label="AC HTRF Laser [Eu](1)",
        custom_info={},
        sample_custom_info={"group identifier": None, "Repeat": 1.0},
        device_control_custom_info={
            "Ambient temperature at start": None,
            "Ambient temperature at end": None,
            "Chamber temperature at end": None,
            "Humidity at start": None,
            "Humidity at end": None,
            "Kinetics": 0.0,
            "ScanX": None,
            "ScanY": None,
            "Inside temperature at start": None,
            "Inside temperature at end": None,
        },
    )

    series = ResultPlateInfo.get_series(reader)
    assert ResultPlateInfo.create(series) == expected


def test_create_plate_info_default_barcode() -> None:
    reader = get_reader_from_lines(
        [
            "Plate information",
            "Plate,Repeat,Barcode,Measured height,Chamber temperature at start,Label,Measinfo,Kinetics,Measurement date,",
            '1,1,"=""""",11.9,23.17,AC HTRF Laser [Eu](1),De=1st Ex=Top Em=Top Wdw=1 (14),0,10/13/2022 3:08:06 PM,',
        ]
    )

    series = ResultPlateInfo.get_series(reader)
    plate = ResultPlateInfo.create(series)
    assert plate and plate.barcode == "Plate 1"

    reader = get_reader_from_lines(
        [
            "Plate information",
            "Plate,Repeat,Barcode,Measured height,Chamber temperature at start,Label,Measinfo,Kinetics,Measurement date,",
            "1,1,,11.9,23.17,AC HTRF Laser [Eu](1),De=1st Ex=Top Em=Top Wdw=1 (14),0,10/13/2022 3:08:06 PM,",
        ]
    )

    series = ResultPlateInfo.get_series(reader)
    plate = ResultPlateInfo.create(series)
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
        Result(
            uuid="TEST_ID_0",
            col="A",
            row="1",
            value=1,
        ),
        Result(
            uuid="TEST_ID_1",
            col="A",
            row="2",
            value=2,
        ),
        Result(
            uuid="TEST_ID_2",
            col="B",
            row="1",
            value=3,
        ),
        Result(
            uuid="TEST_ID_3",
            col="B",
            row="2",
            value=4,
        ),
    ]
    with mock_uuid_generation():
        result_list = create_results(reader)
    assert result_list == expected


def test_create_plates() -> None:
    reader = get_reader_from_lines(
        [
            "Plate information",
            "Plate,Repeat,Barcode,Measured height,Chamber temperature at start,Label,Measinfo,Kinetics,Measurement date,",
            "2,1,,1.1,14.5,AC HTRF Laser [Eu](1),De=2nd Ex=Top Em=Top Wdw=1 (14),0,10/13/2022 3:08:06 PM,",
            "",
            "Background information",
            "Plate,Label,Result,Meastime,MeasInfo,",
            "2,AC HTRF Laser [Eu],0,00:00:00.000,De=1st Ex=Top Em=Top Wdw=1 (14),",
            "2,AC HTRF Laser [Eu],0,00:00:00.000,De=2nd Ex=Top Em=Top Wdw=1 (142),",
            "",
            "Results",
            "6,,7,",
            ",,,",
            ",8,,",
        ]
    )

    expected = PlateList(
        calculated=[],
        results=[
            ResultPlate(
                plate_info=ResultPlateInfo(
                    number="2",
                    barcode="Plate 2",
                    emission_filter_id="2nd",
                    measinfo="De=2nd Ex=Top Em=Top Wdw=1 (14)",
                    measurement_time="10/13/2022 3:08:06 PM",
                    measured_height=1.1,
                    chamber_temperature_at_start=14.5,
                    label="AC HTRF Laser [Eu](1)",
                    custom_info={},
                    sample_custom_info={"group identifier": None, "Repeat": 1.0},
                    device_control_custom_info={
                        "Ambient temperature at start": None,
                        "Ambient temperature at end": None,
                        "Chamber temperature at end": None,
                        "Humidity at start": None,
                        "Humidity at end": None,
                        "Kinetics": 0.0,
                        "ScanX": None,
                        "ScanY": None,
                        "Inside temperature at start": None,
                        "Inside temperature at end": None,
                    },
                ),
                background_infos=[
                    BackgroundInfo(
                        plate_num="2",
                        label="AC HTRF Laser [Eu]",
                        measinfo="De=1st Ex=Top Em=Top Wdw=1 (14)",
                    ),
                    BackgroundInfo(
                        plate_num="2",
                        label="AC HTRF Laser [Eu]",
                        measinfo="De=2nd Ex=Top Em=Top Wdw=1 (142)",
                    ),
                ],
                results=[
                    Result(
                        uuid="TEST_ID_0",
                        col="A",
                        row="1",
                        value=6,
                    ),
                    Result(
                        uuid="TEST_ID_1",
                        col="A",
                        row="3",
                        value=7,
                    ),
                    Result(
                        uuid="TEST_ID_2",
                        col="C",
                        row="2",
                        value=8,
                    ),
                ],
            )
        ],
    )
    with mock_uuid_generation():
        plate = PlateList.create(reader)
    assert plate == expected


def test_create_plates_with_calculated_data() -> None:
    reader = get_reader_from_lines(
        [
            "Plate information",
            "Plate,Repeat,Barcode,Measured height,Chamber temperature at start,Formula,Kinetics,Measurement date,",
            "2,1,,1.1,14.5,Calc 1: General = X / 2 where X = test,0,10/13/2022 3:08:06 PM,",
            "",
            "Background information",
            "Plate,Label,Result,Meastime,MeasInfo,",
            "2,AC HTRF Laser [Eu],0,00:00:00.000,De=1st Ex=Top Em=Top Wdw=1 (14),",
            "2,AC HTRF Laser [Eu],0,00:00:00.000,De=2nd Ex=Top Em=Top Wdw=1 (142),",
            "",
            "Calculated results",
            "3,,3.5,",
            ",,,",
            ",4,,",
        ]
    )

    expected = PlateList(
        results=[],
        calculated=[
            CalculatedPlate(
                plate_info=CalculatedPlateInfo(
                    number="2",
                    barcode="Plate 2",
                    measurement_time="10/13/2022 3:08:06 PM",
                    measured_height=1.1,
                    chamber_temperature_at_start=14.5,
                    formula="Calc 1: General = X / 2 where X = test",
                    name="Calc 1: General",
                ),
                background_infos=[
                    BackgroundInfo(
                        plate_num="2",
                        label="AC HTRF Laser [Eu]",
                        measinfo="De=1st Ex=Top Em=Top Wdw=1 (14)",
                    ),
                    BackgroundInfo(
                        plate_num="2",
                        label="AC HTRF Laser [Eu]",
                        measinfo="De=2nd Ex=Top Em=Top Wdw=1 (142)",
                    ),
                ],
                results=[
                    CalculatedResult(
                        col="A",
                        row="1",
                        value=3,
                    ),
                    CalculatedResult(
                        col="A",
                        row="3",
                        value=3.5,
                    ),
                    CalculatedResult(
                        col="C",
                        row="2",
                        value=4,
                    ),
                ],
            )
        ],
    )
    with mock_uuid_generation():
        plate = PlateList.create(reader)
    assert plate == expected


def test_create_calculated_plate_info() -> None:
    data = SeriesData(
        pd.Series(
            {
                "Plate": "4",
                "Measured height": "44.5",
                "Formula": "Calc 1: General = (X / Y) where X = AC HTRF Laser [Eu](1) Y = AC HTRF Laser [Eu](1)",
                "Measurement date": "10/13/2022 3:08:06 PM",
            }
        )
    )
    calculated_plate_info = CalculatedPlateInfo.create(data)

    expected = CalculatedPlateInfo(
        number="4",
        barcode="Plate 4",
        measurement_time="10/13/2022 3:08:06 PM",
        measured_height=44.5,
        formula="Calc 1: General = (X / Y) where X = AC HTRF Laser [Eu](1) Y = AC HTRF Laser [Eu](1)",
        name="Calc 1: General",
        chamber_temperature_at_start=None,
    )

    assert calculated_plate_info == expected


def test_create_calculated_plate_info_with_no_formula() -> None:
    data = SeriesData(
        pd.Series(
            {
                "Plate": "dummy",
                "Measured height": "0",
                "Measurement date": "10/13/2022 3:08:06 PM",
            }
        )
    )
    msg = "Expected non-null value for Formula."
    with pytest.raises(AllotropeConversionError, match=msg):
        CalculatedPlateInfo.create(data)


def test_create_calculated_plate_info_with_invalid_formula() -> None:
    data = SeriesData(
        pd.Series(
            {
                "Plate": "dummy",
                "Measured height": "0",
                "Formula": "invalid formula",
                "Measurement date": "10/13/2022 3:08:06 PM",
            }
        )
    )
    msg = "Unable to find expected formula name for calculated results section."
    with pytest.raises(AllotropeConversionError, match=msg):
        CalculatedPlateInfo.create(data)


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
    with pytest.raises(
        AllotropeConversionError,
        match="Expected non-null value for Basic assay information.",
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
                "1": {
                    "A": SampleRoleType.unknown_sample_role,
                    "C": SampleRoleType.standard_sample_role,
                },
                "2": {"B": SampleRoleType.control_sample_role},
                "3": {"C": SampleRoleType.sample_role},
            },
        ),
        "2": PlateMap(
            plate_n="2",
            group_n="3",
            sample_role_type_mapping={
                "4": {"A": SampleRoleType.blank_role},
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

    label = Labels.create(reader)
    assert label == expected


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
