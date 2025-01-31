import re
import xml.etree.ElementTree as ET  # noqa: N817

import pytest

from allotropy.allotrope.schema_mappers.adm.electrophoresis.benchling._2024._09.electrophoresis import (
    CalculatedDataItem,
    DataSource,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure import (
    _get_unit_class,
    create_measurement_groups,
    create_metadata,
)
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    BRAND_NAME,
    DETECTION_TYPE,
    DEVICE_TYPE,
    PRODUCT_MANUFACTURER,
    SCREEN_TAPE_MISMATCH_ERROR,
    SOFTWARE_NAME,
)
from allotropy.parsers.utils.values import assert_not_none
from allotropy.testing.utils import mock_uuid_generation
from tests.parsers.agilent_tapestation_analysis.agilent_tapestation_test_data import (
    get_metadata_xml,
    get_samples_xml,
)


def test_create_metadata() -> None:
    metadata = create_metadata(get_metadata_xml(), "users/files/file.txt")
    assert metadata == Metadata(
        file_identifier="file.json",
        file_name="file.txt",
        unc_path="users/files/file.txt",
        analyst="TapeStation User",
        analytical_method_identifier="cfDNA",
        data_system_instance_identifier="TAPESTATIONPC",
        device_identifier="65536",
        equipment_serial_number="DEDAB00201",
        experimental_data_identifier="C:\\cfDNA-Tubes-16.cfDNA",
        method_version=None,
        software_version="3.2.0.22472",
        software_name=SOFTWARE_NAME,
        brand_name=BRAND_NAME,
        product_manufacturer=PRODUCT_MANUFACTURER,
        device_type=DEVICE_TYPE,
        detection_type=DETECTION_TYPE,
    )


@pytest.mark.parametrize(
    "xml_unit, unit",
    (
        ("nt", "#"),
        ("bp", "#"),
        ("kD", "kDa"),
    ),
)
def test__get_unit_class(xml_unit: str, unit: str) -> None:
    assert _get_unit_class(get_metadata_xml(molecular_weight_unit=xml_unit)) == unit


def test__get_unit_class_with_unknown_unit() -> None:
    unit = "not-a-unit"
    msg = f"Unrecognized Molecular Weight Unit: '{unit}'. Expecting one of ['bp', 'kD', 'nt']."
    with pytest.raises(AllotropeConversionError, match=re.escape(msg)):
        _get_unit_class(get_metadata_xml(molecular_weight_unit=unit))


def test_create_metadata_with_rine_version() -> None:
    metadata = create_metadata(get_metadata_xml(rine_version="2.3.4"), "dummy.txt")
    assert metadata.method_version == "2.3.4"


def test_create_metadata_with_din_version() -> None:
    metadata = create_metadata(get_metadata_xml(din_version="1.2.3"), "dummy.txt")
    assert metadata.method_version == "1.2.3"


def testcreate_measurement_groups_without_matching_screen_tape() -> None:
    sample_id = "01-S025-180717-01-899752"
    screen_tape_id = "01-S025-200617-01-899752"
    xml_str = f"""
    <File>
        <ScreenTapes>
            <ScreenTape><ScreenTapeID>{screen_tape_id}</ScreenTapeID></ScreenTape>
            <Empty/>
        </ScreenTapes>
        <Samples>
            <Sample><ScreenTapeID>{sample_id}</ScreenTapeID></Sample>
        </Samples>
    </File>
    """

    expected = SCREEN_TAPE_MISMATCH_ERROR.format(sample_id, [screen_tape_id])
    with pytest.raises(AllotropeConversionError, match=re.escape(expected)):
        create_measurement_groups(ET.fromstring(xml_str))  # noqa: S314


def testcreate_measurement_groups_without_screen_tapes() -> None:
    xml_str = """
    <File>
        <Samples>
            <Sample><ScreenTapeID>01-S025-180717-01-899752</ScreenTapeID></Sample>
        </Samples>
    </File>
    """
    error_msg = "Unable to find 'ScreenTapes' from xml."
    with pytest.raises(AllotropeConversionError, match=error_msg):
        create_measurement_groups(ET.fromstring(xml_str))  # noqa: S314


def testcreate_measurement_groups() -> None:
    with mock_uuid_generation():
        groups, calc_docs = create_measurement_groups(get_samples_xml())

    assert groups == [
        MeasurementGroup(
            measurements=[
                Measurement(
                    identifier="TEST_ID_0",
                    measurement_time="2020-09-20T03:52:58-05:00",
                    compartment_temperature=26.4,
                    location_identifier="A1",
                    sample_identifier="ScreenTape01_A1",
                    description="Ladder Ladder",
                    processed_data=ProcessedData(
                        peaks=[
                            ProcessedDataFeature(
                                identifier="TEST_ID_1",
                                name="-",
                                height=261.379,
                                start=68.0,
                                start_unit="#",
                                end=158.0,
                                end_unit="#",
                                position=100.0,
                                position_unit="#",
                                area=1.0,
                                relative_area=None,
                                relative_corrected_area=None,
                                comment="Lower Marker",
                            ),
                            ProcessedDataFeature(
                                identifier="TEST_ID_2",
                                name="1",
                                height=284.723,
                                start=3812.0,
                                start_unit="#",
                                end=None,
                                end_unit="#",
                                position=8525.0,
                                position_unit="#",
                                area=1.33,
                                relative_area=44.38,
                                relative_corrected_area=92.30,
                                comment=None,
                            ),
                        ],
                        data_regions=[],
                    ),
                    errors=None,
                )
            ]
        )
    ]
    assert not calc_docs


def testcreate_measurement_groups_with_calculated_data() -> None:
    with mock_uuid_generation():
        _, calc_docs = create_measurement_groups(
            get_samples_xml(with_calculated_data=True)
        )

    sample_data_source = DataSource(feature="sample", identifier="TEST_ID_0")
    peak_1_data_source = DataSource(feature="peak", identifier="TEST_ID_2")
    peak_2_data_source = DataSource(feature="peak", identifier="TEST_ID_7")

    assert calc_docs == [
        CalculatedDataItem(
            identifier="TEST_ID_1",
            name="Concentration",
            unit="(unitless)",
            value=58.2,
            data_sources=[sample_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_3",
            name="AssignedQuantity",
            unit="(unitless)",
            value=8.50,
            data_sources=[peak_1_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_4",
            name="FromPercent",
            unit="(unitless)",
            value=80.6,
            data_sources=[peak_1_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_5",
            name="Molarity",
            unit="(unitless)",
            value=131.0,
            data_sources=[peak_1_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_6",
            name="ToPercent",
            unit="(unitless)",
            value=85.4,
            data_sources=[peak_1_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_8",
            name="CalibratedQuantity",
            unit="(unitless)",
            value=11.3,
            data_sources=[peak_2_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_9",
            name="FromPercent",
            unit="(unitless)",
            value=41.1,
            data_sources=[peak_2_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_10",
            name="RunDistance",
            unit="(unitless)",
            value=46.5,
            data_sources=[peak_2_data_source],
        ),
    ]


def testcreate_measurement_groups_with_error() -> None:
    groups, _ = create_measurement_groups(get_samples_xml(sample_error="Sample Error."))
    assert assert_not_none(groups[0].measurements[0].errors)[0].error == "Sample Error."


def testcreate_measurement_groups_with_regions() -> None:
    with mock_uuid_generation():
        groups, calc_docs = create_measurement_groups(
            get_samples_xml(with_regions=True)
        )

    region_1_data_source = DataSource(feature="data region", identifier="TEST_ID_3")
    region_2_data_source = DataSource(feature="data region", identifier="TEST_ID_6")

    # Note: Data regions are ordered by <From> (region_start) ascending
    assert groups[0].measurements[0].processed_data.data_regions == [
        ProcessedDataFeature(
            identifier="TEST_ID_3",
            start=42.0,
            start_unit="#",
            end=3000.0,
            end_unit="#",
            area=0.10,
            relative_area=3.17,
            name="1",
            comment="Partially Degraded",
        ),
        ProcessedDataFeature(
            identifier="TEST_ID_6",
            start=504.0,
            start_unit="#",
            end=1000.0,
            end_unit="#",
            area=0.13,
            relative_area=4.09,
            name="2",
            comment="Degraded",
        ),
    ]
    assert calc_docs == [
        CalculatedDataItem(
            identifier="TEST_ID_4",
            name="AverageSize",
            unit="(unitless)",
            value=1944.0,
            data_sources=[region_1_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_5",
            name="Molarity",
            unit="(unitless)",
            value=0.765,
            data_sources=[region_1_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_7",
            name="AverageSize",
            unit="(unitless)",
            value=395.0,
            data_sources=[region_2_data_source],
        ),
        CalculatedDataItem(
            identifier="TEST_ID_8",
            name="Concentration",
            unit="(unitless)",
            value=1.11,
            data_sources=[region_2_data_source],
        ),
    ]
