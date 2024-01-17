from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import Data, Header


def test_create_data() -> None:
    reader = LinesReader(
        [
            "Program,xPONENT,,FlexMAP 3D,,,,,,,,,,,,,,,,,,,,",
            "Build,4.3.229.0,,,,,,,,,,,,,,,,,,,,,,",
            "Date,05/17/2023,6:42 PM,,,,,,,,,,,,,,,,,,,,,",
            ",,,,,,,,,,,,,,,,,,,,,,,",
            "SN,FM3DD12341234,,,,,,,,,,,,,,,,,,,,,,",
            "Batch,ABCD_1234_20231225,,,,,,,,,,,,,,,,,,,,,,",
            "Version,1,,,,,,,,,,,,,,,,,,,,,,",
            "Operator,waldo,,,,,,,,,,,,,,,,,,,,,,",
            "ComputerName,ABCDEFG123456,,,,,,,,,,,,,,,,,,,,,,",
            "Country Code,7F,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolName,foo_bar,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolVersion,3,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolDescription,baz,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolDevelopingCompany,qux,,,,,,,,,,,,,,,,,,,,,,",
            "SampleVolume,50 uL,,,,,,,,,,,,,,,,,,,,,,",
            "DDGate,5000 to 25000,,,,,,,,,,,,,,,,,,,,,,",
            "SampleTimeout,0 sec,,,,,,,,,,,,,,,,,,,,,,",
            "BatchStartTime,5/17/2023 6:42:29 PM,,,,,,,,,,,,,,,,,,,,,,",
            "BatchStopTime,5/17/2023 7:06:59 PM,,,,,,,,,,,,,,,,,,,,,,",
            "BatchDescription,<None>,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolPlate,Name,Current 96-well plate,Type,96,Plates,1,,,,,,,,,,,,,,,,,",
            "ProtocolMicrosphere,Map,FlexMAP 3D Map,Type,MagPlex,Count,21,,,,,,,,,,,,,,,,,",
            "ProtocolReporterGain,Standard PMT,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolAnalysis,Off,,,,,,,,,,,,,,,,,,,,,,",
            "NormBead,None,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolHeater,Off,,,,,,,,,,,,,,,,,,,,,,",
            ",,,,,,,,,,,,,,,,,,,,,,,",
            "Most Recent Calibration and Verification Results:,,,,,,,,,,,,,,,,,,,,,,,",
        ]
    )

    data = Data.create(reader)

    assert data == Data(
        header=Header(
            model_number="FlexMAP 3D",  # Program, col 4
            equipment_serial_number="FM3DD12341234",  # SN
            analytical_method_identifier="foo_bar",  # ProtocolName
            method_version="3",  # ProtocolVersion
            experimental_data_identifier="ABCD_1234_20231225",  # Batch
            sample_volume="50 uL",  # SampleVolume
            plate_well_count=96,  # ProtocolPlate, column 5 (after Type)
            measurement_time="2023-05-17T18:42:29",  # BatchStartTime  MM/DD/YYY HH:MM:SS %p ->  YYYY-MM-DD HH:MM:SS
            detector_gain_setting="Standard PMT",  # ProtocolReporterGain
            analyst="waldo",  # Operator row
        )
    )
