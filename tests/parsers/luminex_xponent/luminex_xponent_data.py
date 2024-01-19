from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    CalibrationItem,
    Data,
    Header,
)


def get_reader() -> CsvReader:
    return CsvReader(
        [
            "Program,xPONENT,,FlexMAP 3D,,,,,,,,,,,,,,,,,,,,",
            "Build,4.3.229.0,,,,,,,,,,,,,,,,,,,,,,",
            "Date,05/17/2023,6:42 PM,,,,,,,,,,,,,,,,,,,,,",
            ",,,,,,,,,,,,,,,,,,,,,,,",
            "SN,FM3DD12341234,,,,,,,,,,,,,,,,,,,,,,",
            "Batch,ABCD_1234_20231225,,,,,,,,,,,,,,,,,,,,,,",
            "Operator,waldo,,,,,,,,,,,,,,,,,,,,,,",
            "ComputerName,ABCDEFG123456,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolName,foo_bar,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolVersion,3,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolDescription,baz,,,,,,,,,,,,,,,,,,,,,,",
            "SampleVolume,50 uL,,,,,,,,,,,,,,,,,,,,,,",
            "BatchStartTime,5/17/2023 6:42:29 PM,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolPlate,Name,Current 96-well plate,Type,96,Plates,1,,,,,,,,,,,,,,,,,",
            "ProtocolMicrosphere,Map,FlexMAP 3D Map,Type,MagPlex,Count,21,,,,,,,,,,,,,,,,,",
            "ProtocolReporterGain,Standard PMT,,,,,,,,,,,,,,,,,,,,,,",
            "ProtocolAnalysis,Off,,,,,,,,,,,,,,,,,,,,,,",
            ",,,,,,,,,,,,,,,,,,,,,,,",
            "Most Recent Calibration and Verification Results:,,,,,,,,,,,,,,,,,,,,,,,",
            "Last F3DeCAL1 Calibration,Passed 05/17/2023 09:25:11,,,,,,,,,,,,,,,,,,,,,,",
            "Last F3DCAL2 Calibration,Failed 05/17/2023 09:25:33,,,,,,,,,,,,,,,,,,,,,,",
            "Last Fluidics Test,Passed 05/17/2023 09:28:43,,,,,,,,,,,,,,,,,,,,,,",
            ",,,,,,,,,,,,,,,,,,,,,,,",
            "CALInfo:,,,,,,,,,,,,,,,,,,,,,,,",
        ]
    )


def get_data() -> Data:
    return Data(
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
            data_system_instance_identifier="ABCDEFG123456",  # ComputerName
        ),
        calibration_data=[
            CalibrationItem(
                name="F3DeCAL1 Calibration",
                report="Passed",
                time="2023-05-17T09:25:11",
            ),
            CalibrationItem(
                name="F3DCAL2 Calibration",
                report="Failed",
                time="2023-05-17T09:25:33",
            ),
            CalibrationItem(
                name="Fluidics Test",
                report="Passed",
                time="2023-05-17T09:28:43",
            ),
        ],
    )
