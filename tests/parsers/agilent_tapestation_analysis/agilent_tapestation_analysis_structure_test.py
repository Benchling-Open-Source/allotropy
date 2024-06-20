from unittest import mock
import pytest

import xml.etree.ElementTree as ET

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure import (
    MetaData,
    Sample,
    SamplesList,
)
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    NO_SCREEN_TAPE_ID_MATCH,
)
from tests.parsers.agilent_tapestation_analysis.agilent_tapestation_test_data import (
    get_metadata_xml,
    get_samples_xml,
)


@pytest.mark.short
def test_create_metadata() -> None:
    metadata = MetaData.create(get_metadata_xml())
    assert metadata == MetaData(
        analyst="TapeStation User",
        analytical_method_identifier="cfDNA",
        data_system_instance_identifier="TAPESTATIONPC",
        device_identifier="65536",
        equipment_serial_number="DEDAB00201",
        experimental_data_identifier="C:\\cfDNA-Tubes-16.cfDNA",
        method_version=None,
        software_version="3.2.0.22472",
    )


@pytest.mark.short
def test_create_metadata_with_rine_version() -> None:
    metadata = MetaData.create(get_metadata_xml(rine_version="2.3.4"))
    assert metadata.method_version == "2.3.4"


@pytest.mark.short
def test_create_metadata_with_din_version() -> None:
    metadata = MetaData.create(get_metadata_xml(din_version="1.2.3"))
    assert metadata.method_version == "1.2.3"


@pytest.mark.short
def test_create_samples_list_without_matching_screen_tape() -> None:
    xml_str = """
    <File>
        <ScreenTapes>
            <ScreenTape><ScreenTapeID>01-S025-200617-01-899752</ScreenTapeID></ScreenTape>
        </ScreenTapes>
        <Samples>
            <Sample><ScreenTapeID>01-S025-180717-01-899752</ScreenTapeID></Sample>
        </Samples>
    </File>
    """
    error_msg = NO_SCREEN_TAPE_ID_MATCH.format("01-S025-180717-01-899752")
    with pytest.raises(AllotropeConversionError, match=error_msg):
        SamplesList.create(ET.fromstring(xml_str))  # noqa: S314


@pytest.mark.short
def test_create_samples_list_without_screen_tapes() -> None:
    xml_str = """
    <File>
        <Samples>
            <Sample><ScreenTapeID>01-S025-180717-01-899752</ScreenTapeID></Sample>
        </Samples>
    </File>
    """
    error_msg = "Unable to find 'ScreenTapes' from xml."
    with pytest.raises(AllotropeConversionError, match=error_msg):
        SamplesList.create(ET.fromstring(xml_str))  # noqa: S314


@pytest.mark.short
def test_create_samples_list() -> None:
    with mock.patch(
        "allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure.random_uuid_str",
        return_value="dummy_id",
    ):
        samples_list = SamplesList.create(get_samples_xml())

    assert samples_list == SamplesList(
        samples=[
            Sample(
                measurement_id="dummy_id",
                measurement_time="2020-09-20T03:52:58-05:00",
                compartment_temperature=26.4,
                location_identifier="A1",
                sample_identifier="ScreenTape01_A1",
                description="Ladder Ladder",
            )
        ]
    )
