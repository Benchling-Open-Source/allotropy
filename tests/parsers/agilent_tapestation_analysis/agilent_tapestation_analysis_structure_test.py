from unittest import mock
import xml.etree.ElementTree as ET  # noqa: N817

import pytest

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueKiloDalton,
    TQuantityValueNumber,
)
from allotropy.allotrope.models.shared.definitions.definitions import InvalidJsonFloat
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure import (
    DataRegion,
    MetaData,
    Peak,
    Sample,
    SamplesList,
)
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    NO_SCREEN_TAPE_ID_MATCH,
    PEAK_UNIT_CLASSES,
)
from tests.parsers.agilent_tapestation_analysis.agilent_tapestation_test_data import (
    get_metadata_xml,
    get_samples_xml,
)


@pytest.mark.short
def test_create_metadata() -> None:
    metadata = MetaData.create(get_metadata_xml())
    assert metadata == MetaData(
        peak_unit_cls=TQuantityValueNumber,
        analyst="TapeStation User",
        analytical_method_identifier="cfDNA",
        data_system_instance_identifier="TAPESTATIONPC",
        device_identifier="65536",
        equipment_serial_number="DEDAB00201",
        experimental_data_identifier="C:\\cfDNA-Tubes-16.cfDNA",
        method_version=None,
        software_version="3.2.0.22472",
    )


@pytest.mark.parametrize(
    "unit, unit_class",
    (
        ("nt", TQuantityValueNumber),
        ("bp", TQuantityValueNumber),
        ("kD", TQuantityValueKiloDalton),
    ),
)
@pytest.mark.short
def test_create_metadata_with_unit(unit: str, unit_class: PEAK_UNIT_CLASSES) -> None:
    metadata = MetaData.create(get_metadata_xml(molecular_weight_unit=unit))
    assert metadata.peak_unit_cls == unit_class


@pytest.mark.short
def test_create_metadata_with_unknown_unit() -> None:
    unit = "not-a-unit"
    msg = f"Unrecognized Molecular Weight Unit: {unit}"
    with pytest.raises(AllotropeConversionError, match=msg):
        MetaData.create(get_metadata_xml(molecular_weight_unit=unit))


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
            <Empty/>
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

    assert samples_list.samples == [
        Sample(
            measurement_id="dummy_id",
            measurement_time="2020-09-20T03:52:58-05:00",
            compartment_temperature=26.4,
            location_identifier="A1",
            sample_identifier="ScreenTape01_A1",
            description="Ladder Ladder",
            peak_list=[
                Peak(
                    peak_identifier="dummy_id",
                    peak_name="-",
                    peak_height=261.379,
                    peak_start=68,
                    peak_end=158,
                    peak_position=100,
                    peak_area=1.0,
                    relative_peak_area=InvalidJsonFloat.NaN,
                    relative_corrected_peak_area=InvalidJsonFloat.NaN,
                    comment="Lower Marker",
                ),
                Peak(
                    peak_identifier="dummy_id",
                    peak_name="1",
                    peak_height=284.723,
                    peak_start=3812,
                    peak_end=InvalidJsonFloat.NaN,
                    peak_position=8525,
                    peak_area=1.33,
                    relative_peak_area=44.38,
                    relative_corrected_peak_area=92.30,
                    comment=None,
                ),
            ],
            data_regions=[],
        )
    ]


@pytest.mark.short
def test_create_samples_list_with_regions() -> None:
    with mock.patch(
        "allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure.random_uuid_str",
        return_value="dummy_id",
    ):
        samples_list = SamplesList.create(get_samples_xml(include_regions=True))
    assert samples_list.samples[0].data_regions == [
        DataRegion(
            region_identifier="dummy_id",
            region_start=42,
            region_end=3000,
            region_area=0.10,
            relative_region_area=3.17,
            region_name="1",
            comment="Partially Degraded",
        ),
        DataRegion(
            region_identifier="dummy_id",
            region_start=504,
            region_end=1000,
            region_area=0.13,
            relative_region_area=4.09,
            region_name="2",
            comment="Degraded",
        ),
    ]
