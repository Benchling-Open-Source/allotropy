import pytest

import xml.etree.ElementTree as ET

from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure import (
    MetaData,
)


def _get_metadata_xml(
    rine_version: str | None = None, din_version: str | None = None
) -> str:
    method_version = ""
    if rine_version:
        method_version = f"<RINeVersion>{rine_version}</RINeVersion>"
    elif din_version:
        method_version = f"<DINVersion>{din_version}</DINVersion>"

    xml_str = f"""
    <File>
        <FileInformation>
            <FileName>C:\cfDNA-Tubes-16.cfDNA</FileName>
            <Assay>cfDNA</Assay>
            {method_version}
        </FileInformation>
        <ScreenTapes>
            <ScreenTape>
                <Environment>
                    <Experimenter>TapeStation User</Experimenter>
                    <InstrumentType>65536</InstrumentType>
                    <InstrumentSerialNumber>DEDAB00201</InstrumentSerialNumber>
                    <Computer>TAPESTATIONPC</Computer>
                    <AnalysisVersion>3.2.0.22472</AnalysisVersion>
                </Environment>
            </ScreenTape>
        </ScreenTapes>
    </File>
    """
    return xml_str


@pytest.mark.short
def test_create_metadata() -> None:
    xml_str = _get_metadata_xml()
    metadata = MetaData.create(ET.fromstring(xml_str))
    assert metadata == MetaData(
        analyst="TapeStation User",
        analytical_method_identifier="cfDNA",
        data_system_instance_identifier="TAPESTATIONPC",
        device_identifier="65536",
        equipment_serial_number="DEDAB00201",
        experimental_data_identifier="C:\cfDNA-Tubes-16.cfDNA",
        method_version=None,
        software_version="3.2.0.22472",
    )


@pytest.mark.short
def test_create_metadata_with_rine_version() -> None:
    xml_str = _get_metadata_xml(rine_version="2.3.4")
    metadata = MetaData.create(ET.fromstring(xml_str))
    assert metadata.method_version == "2.3.4"


@pytest.mark.short
def test_create_metadata_with_din_version() -> None:
    xml_str = _get_metadata_xml(din_version="1.2.3")
    metadata = MetaData.create(ET.fromstring(xml_str))
    assert metadata.method_version == "1.2.3"
