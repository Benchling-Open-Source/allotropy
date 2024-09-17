from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Analyte,
    Calibration,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.luminex_xponent.luminex_xponent_reader import (
    LuminexXponentReader,
)
from allotropy.parsers.luminex_xponent.luminex_xponent_structure import (
    Data,
    Header,
    Measurement,
    MeasurementList,
)


def get_reader() -> LuminexXponentReader:
    filename = "tests/parsers/luminex_xponent/testdata/test_data_exclude.csv"
    with open(filename, "rb") as fp:
        return LuminexXponentReader(NamedFileContents(fp, filename))


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
            minimum_assay_bead_count_setting=100,
        ),
        calibrations=[
            Calibration(
                name="F3DeCAL1 Calibration",
                report="Passed",
                time="05/17/2023 09:25:11",
            ),
            Calibration(
                name="F3DCAL2 Calibration",
                report="Failed",
                time="05/17/2023 09:25:33",
            ),
            Calibration(
                name="Fluidics Test",
                report="Passed",
                time="05/17/2023 09:28:43",
            ),
        ],
        measurement_list=MeasurementList(
            measurements=[
                Measurement(
                    identifier="dummy_id",
                    sample_identifier="Unknown1",
                    location_identifier="A1",
                    dilution_factor_setting=1,
                    assay_bead_count=881.0,
                    analytes=[
                        Analyte(
                            identifier="dummy_id",
                            name="alpha",
                            assay_bead_identifier="28",
                            assay_bead_count=30.0,
                            value=10921.5,
                            statistic_datum_role=TStatisticDatumRole.median_role,
                        ),
                        Analyte(
                            identifier="dummy_id",
                            name="bravo",
                            assay_bead_identifier="35",
                            assay_bead_count=42.0,
                            value=37214.0,
                            statistic_datum_role=TStatisticDatumRole.median_role,
                        ),
                        Analyte(
                            identifier="dummy_id",
                            name="charlie",
                            assay_bead_identifier="37",
                            assay_bead_count=42.0,
                            value=24978.0,
                            statistic_datum_role=TStatisticDatumRole.median_role,
                        ),
                    ],
                    errors=[
                        "maximum count.  (0x4FF010AB)",
                        "specified count.",
                    ],
                ),
                Measurement(
                    identifier="dummy_id",
                    sample_identifier="Unknown2",
                    location_identifier="B1",
                    dilution_factor_setting=3.0,
                    assay_bead_count=728.0,
                    analytes=[
                        Analyte(
                            identifier="dummy_id",
                            name="alpha",
                            assay_bead_identifier="28",
                            assay_bead_count=26.0,
                            value=8244.0,
                            statistic_datum_role=TStatisticDatumRole.median_role,
                        ),
                        Analyte(
                            identifier="dummy_id",
                            name="bravo",
                            assay_bead_identifier="35",
                            assay_bead_count=33.0,
                            value=35052.0,
                            statistic_datum_role=TStatisticDatumRole.median_role,
                        ),
                        Analyte(
                            identifier="dummy_id",
                            name="charlie",
                            assay_bead_identifier="37",
                            assay_bead_count=33.0,
                            value=22609.0,
                            statistic_datum_role=TStatisticDatumRole.median_role,
                        ),
                    ],
                ),
            ]
        ),
    )
