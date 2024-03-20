import pandas as pd
import pytest

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    ScanPositionSettingPlateReader,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    BackgroundInfo,
    BackgroundInfoList,
    BasicAssayInfo,
    CalculatedPlateInfo,
    CalculatedResult,
    CalculatedResultList,
    create_plate_maps,
    Filter,
    Instrument,
    Labels,
    Plate,
    PlateList,
    PlateMap,
    PlateType,
    Result,
    ResultList,
    ResultPlateInfo,
)


def get_reader_from_lines(lines: list[str]) -> CsvReader:
    return CsvReader(lines)


def rm_result_list_uuids(result_list: ResultList) -> ResultList:
    for result in result_list.results:
        result.uuid = ""
    return result_list


def rm_calculated_result_list_uuid(
    calculated_result_list: CalculatedResultList,
) -> CalculatedResultList:
    for calculated_result in calculated_result_list.calculated_results:
        calculated_result.uuid = ""
    return calculated_result_list


def rm_plate_uuids(plate: Plate) -> Plate:
    plate.calculated_result_list = rm_calculated_result_list_uuid(
        plate.calculated_result_list
    )
    plate.result_list = rm_result_list_uuids(plate.result_list)
    return plate


def rm_plates_uuids(plates: PlateList) -> PlateList:
    return PlateList([rm_plate_uuids(plate) for plate in plates.plates])


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

    expected = ResultList(
        results=[
            Result(
                uuid="419c6bf1-25a7-448a-a201-67745003a1c5",
                col="A",
                row="01",
                value=1,
            ),
            Result(
                uuid="e2390200-ce45-44dc-b012-a98139a2981c",
                col="A",
                row="02",
                value=2,
            ),
            Result(
                uuid="334db986-6007-4f36-8250-b8b3b6a47032",
                col="B",
                row="01",
                value=3,
            ),
            Result(
                uuid="055ecf25-af94-484d-b44e-584b55a0c553",
                col="B",
                row="02",
                value=4,
            ),
        ]
    )
    result_list = ResultList.create(reader)
    assert rm_result_list_uuids(result_list) == rm_result_list_uuids(expected)


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
        plates=[
            Plate(
                plate_info=ResultPlateInfo(
                    number="2",
                    barcode="Plate 2",
                    emission_filter_id="2nd",
                    measinfo="De=2nd Ex=Top Em=Top Wdw=1 (14)",
                    measurement_time="10/13/2022 3:08:06 PM",
                    measured_height=1.1,
                    chamber_temperature_at_start=14.5,
                    label="AC HTRF Laser [Eu](1)",
                ),
                background_info_list=BackgroundInfoList(
                    background_info=[
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
                ),
                calculated_result_list=CalculatedResultList([]),
                result_list=ResultList(
                    results=[
                        Result(
                            uuid="68893bf4-218e-45ed-9622-01e9211a2608",
                            col="A",
                            row="01",
                            value=6,
                        ),
                        Result(
                            uuid="d549e030-8fe2-4a24-8d58-f6abdf5010d6",
                            col="A",
                            row="03",
                            value=7,
                        ),
                        Result(
                            uuid="1a82a766-5ff6-4b02-9d4f-3d2fe71ea55e",
                            col="C",
                            row="02",
                            value=8,
                        ),
                    ]
                ),
            )
        ]
    )

    plate = PlateList.create(reader)
    assert rm_plates_uuids(plate) == rm_plates_uuids(expected)


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
        [
            Plate(
                plate_info=CalculatedPlateInfo(
                    number="2",
                    barcode="Plate 2",
                    measurement_time="10/13/2022 3:08:06 PM",
                    measured_height=1.1,
                    chamber_temperature_at_start=14.5,
                    formula="Calc 1: General = X / 2 where X = test",
                    name="Calc 1: General",
                ),
                background_info_list=BackgroundInfoList(
                    background_info=[
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
                ),
                calculated_result_list=CalculatedResultList(
                    calculated_results=[
                        CalculatedResult(
                            uuid="68893bf4-218e-45ed-9622-01e9211a2608",
                            col="A",
                            row="01",
                            value=3,
                        ),
                        CalculatedResult(
                            uuid="d549e030-8fe2-4a24-8d58-f6abdf5010d6",
                            col="A",
                            row="03",
                            value=3.5,
                        ),
                        CalculatedResult(
                            uuid="1a82a766-5ff6-4b02-9d4f-3d2fe71ea55e",
                            col="C",
                            row="02",
                            value=4,
                        ),
                    ]
                ),
                result_list=ResultList([]),
            )
        ]
    )

    plate = PlateList.create(reader)
    assert rm_plates_uuids(plate) == rm_plates_uuids(expected)


def test_create_calculated_plate_info() -> None:
    data = pd.Series(
        {
            "Plate": "4",
            "Measured height": "44.5",
            "Formula": "Calc 1: General = (X / Y) where X = AC HTRF Laser [Eu](1) Y = AC HTRF Laser [Eu](1)",
            "Measurement date": "10/13/2022 3:08:06 PM",
        }
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
    data = pd.Series(
        {
            "Plate": "dummy",
            "Measured height": "0",
            "Measurement date": "10/13/2022 3:08:06 PM",
        }
    )
    msg = "Unable to find expected formula for calculated results section."
    with pytest.raises(AllotropeConversionError, match=msg):
        CalculatedPlateInfo.create(data)


def test_create_calculated_plate_info_with_invalid_formula() -> None:
    data = pd.Series(
        {
            "Plate": "dummy",
            "Measured height": "0",
            "Formula": "invalid formula",
            "Measurement date": "10/13/2022 3:08:06 PM",
        }
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
