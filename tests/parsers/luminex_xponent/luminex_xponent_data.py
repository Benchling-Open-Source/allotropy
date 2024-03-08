from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    Analyte,
    CalibrationItem,
    Data,
    Header,
    Measurement,
    MeasurementList,
)


def get_reader() -> CsvReader:
    filename = "tests/parsers/luminex_xponent/testdata/test_data.csv"
    with open(filename, "rb") as fp:
        named_file_contents = NamedFileContents(fp, filename)
        lines = read_to_lines(named_file_contents)
    return CsvReader(lines)


def get_data() -> Data:
    return Data(
        header=Header(
            model_number="FlexMAP 3D",  # Program, col 4
            equipment_serial_number="FM3DD12341234",  # SN
            software_version="4.3.229.0",  # Build
            analytical_method_identifier="foo_bar",  # ProtocolName
            method_version="3",  # ProtocolVersion
            experimental_data_identifier="ABCD_1234_20231225",  # Batch
            sample_volume_setting=50,  # SampleVolume
            plate_well_count=96,  # ProtocolPlate, column 5 (after Type)
            measurement_time="5/17/2023 6:42:29 PM",  # BatchStartTime  MM/DD/YYY HH:MM:SS %p ->  YYYY-MM-DD HH:MM:SS
            detector_gain_setting="Standard PMT",  # ProtocolReporterGain
            analyst="waldo",  # Operator row
            data_system_instance_identifier="ABCDEFG123456",  # ComputerName
        ),
        calibration_data=[
            CalibrationItem(
                name="F3DeCAL1 Calibration",
                report="Passed",
                time="05/17/2023 09:25:11",
            ),
            CalibrationItem(
                name="F3DCAL2 Calibration",
                report="Failed",
                time="05/17/2023 09:25:33",
            ),
            CalibrationItem(
                name="Fluidics Test",
                report="Passed",
                time="05/17/2023 09:28:43",
            ),
        ],
        minimum_bead_count_setting=100,
        measurement_list=MeasurementList(
            measurements=[
                Measurement(
                    sample_identifier="Unknown1",
                    location_identifier="A1",
                    dilution_factor_setting=1,
                    assay_bead_count=881.0,
                    analytes=[
                        Analyte(
                            analyte_name="alpha",
                            assay_bead_identifier="28",
                            assay_bead_count=30,
                            fluorescence=10921.5,
                        ),
                        Analyte(
                            analyte_name="bravo",
                            assay_bead_identifier="35",
                            assay_bead_count=42,
                            fluorescence=37214,
                        ),
                        Analyte(
                            analyte_name="charlie",
                            assay_bead_identifier="37",
                            assay_bead_count=42,
                            fluorescence=24978,
                        ),
                    ],
                    errors=[
                        "maximum count.  (0x4FF010AB)",
                        "specified count.",
                    ],
                ),
                Measurement(
                    sample_identifier="Unknown2",
                    location_identifier="B1",
                    dilution_factor_setting=3,
                    assay_bead_count=728.0,
                    analytes=[
                        Analyte(
                            analyte_name="alpha",
                            assay_bead_identifier="28",
                            assay_bead_count=26,
                            fluorescence=8244,
                        ),
                        Analyte(
                            analyte_name="bravo",
                            assay_bead_identifier="35",
                            assay_bead_count=33,
                            fluorescence=35052,
                        ),
                        Analyte(
                            analyte_name="charlie",
                            assay_bead_identifier="37",
                            assay_bead_count=33,
                            fluorescence=22609,
                        ),
                    ],
                ),
            ]
        ),
    )
