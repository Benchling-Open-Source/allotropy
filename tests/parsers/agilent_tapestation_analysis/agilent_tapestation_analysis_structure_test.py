import re
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
    Metadata,
    Peak,
    Sample,
    SamplesList,
)
from allotropy.parsers.agilent_tapestation_analysis.constants import UNIT_CLASSES
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from tests.parsers.agilent_tapestation_analysis.agilent_tapestation_test_data import (
    get_metadata_xml,
    get_samples_xml,
)


@pytest.mark.short
def test_create_metadata() -> None:
    metadata = Metadata.create(get_metadata_xml())
    assert metadata == Metadata(
        unit_cls=TQuantityValueNumber,
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
def test_create_metadata_with_unit(unit: str, unit_class: UNIT_CLASSES) -> None:
    metadata = Metadata.create(get_metadata_xml(molecular_weight_unit=unit))
    assert metadata.unit_cls == unit_class


@pytest.mark.short
def test_create_metadata_with_unknown_unit() -> None:
    unit = "not-a-unit"
    msg = f"Unrecognized Molecular Weight Unit: '{unit}'. Expecting one of ['bp', 'kD', 'nt']."
    with pytest.raises(AllotropeConversionError, match=re.escape(msg)):
        Metadata.create(get_metadata_xml(molecular_weight_unit=unit))


@pytest.mark.short
def test_create_metadata_with_rine_version() -> None:
    metadata = Metadata.create(get_metadata_xml(rine_version="2.3.4"))
    assert metadata.method_version == "2.3.4"


@pytest.mark.short
def test_create_metadata_with_din_version() -> None:
    metadata = Metadata.create(get_metadata_xml(din_version="1.2.3"))
    assert metadata.method_version == "1.2.3"


@pytest.mark.short
def test_create_samples_list_without_matching_screen_tape() -> None:
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
    expected = f"Unrecognized ScreenTape ID: '{sample_id}'. Expecting one of ['{screen_tape_id}']."
    with pytest.raises(AllotropeConversionError, match=re.escape(expected)):
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
            measurement_identifier="dummy_id",
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
                    peak_start=68.0,
                    peak_end=158.0,
                    peak_position=100.0,
                    peak_area=1.0,
                    relative_peak_area=InvalidJsonFloat.NaN,
                    relative_corrected_peak_area=InvalidJsonFloat.NaN,
                    comment="Lower Marker",
                    calculated_data=[],
                ),
                Peak(
                    peak_identifier="dummy_id",
                    peak_name="1",
                    peak_height=284.723,
                    peak_start=3812.0,
                    peak_end=InvalidJsonFloat.NaN,
                    peak_position=8525.0,
                    peak_area=1.33,
                    relative_peak_area=44.38,
                    relative_corrected_peak_area=92.30,
                    comment=None,
                    calculated_data=[],
                ),
            ],
            data_regions=[],
            calculated_data=[],
            error=None,
        )
    ]


@pytest.mark.short
def test_create_samples_list_with_calculated_data() -> None:
    with mock.patch(
        "allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure.random_uuid_str",
        return_value="dummy_id",
    ):
        samples_list = SamplesList.create(get_samples_xml(with_calculated_data=True))

    peak_data_source = DataSource(
        feature="peak", reference=Referenceable(uuid="dummy_id")
    )
    sample_data_source = DataSource(
        feature="sample", reference=Referenceable(uuid="dummy_id")
    )

    sample = samples_list.samples[0]

    assert sample.calculated_data == [
        CalculatedDocument(
            uuid="dummy_id",
            name="Concentration",
            value=58.2,
            data_sources=[sample_data_source],
        )
    ]
    assert sample.peak_list[0].calculated_data == [
        CalculatedDocument(
            uuid="dummy_id",
            name="AssignedQuantity",
            value=8.50,
            data_sources=[peak_data_source],
        ),
        CalculatedDocument(
            uuid="dummy_id",
            name="FromPercent",
            value=80.6,
            data_sources=[peak_data_source],
        ),
        CalculatedDocument(
            uuid="dummy_id",
            name="Molarity",
            value=131.0,
            data_sources=[peak_data_source],
        ),
        CalculatedDocument(
            uuid="dummy_id",
            name="ToPercent",
            value=85.4,
            data_sources=[peak_data_source],
        ),
    ]
    assert sample.peak_list[1].calculated_data == [
        CalculatedDocument(
            uuid="dummy_id",
            name="CalibratedQuantity",
            value=11.3,
            data_sources=[peak_data_source],
        ),
        CalculatedDocument(
            uuid="dummy_id",
            name="FromPercent",
            value=41.1,
            data_sources=[peak_data_source],
        ),
        CalculatedDocument(
            uuid="dummy_id",
            name="RunDistance",
            value=46.5,
            data_sources=[peak_data_source],
        ),
    ]


@pytest.mark.short
def test_create_samples_list_with_error() -> None:
    samples_list = SamplesList.create(get_samples_xml(sample_error="Sample Error."))
    assert samples_list.samples[0].error == "Sample Error."


@pytest.mark.short
def test_create_samples_list_with_regions() -> None:
    with mock.patch(
        "allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure.random_uuid_str",
        return_value="dummy_id",
    ):
        samples_list = SamplesList.create(get_samples_xml(with_regions=True))
    region_data_source = DataSource(
        feature="data region", reference=Referenceable(uuid="dummy_id")
    )

    # Note: Data regions are ordered by <From> (region_start) ascending
    assert samples_list.samples[0].data_regions == [
        DataRegion(
            region_identifier="dummy_id",
            region_start=42.0,
            region_end=3000.0,
            region_area=0.10,
            relative_region_area=3.17,
            region_name="1",
            comment="Partially Degraded",
            calculated_data=[
                CalculatedDocument(
                    uuid="dummy_id",
                    name="AverageSize",
                    value=1944.0,
                    data_sources=[region_data_source],
                ),
                CalculatedDocument(
                    uuid="dummy_id",
                    name="Molarity",
                    value=0.765,
                    data_sources=[region_data_source],
                ),
            ],
        ),
        DataRegion(
            region_identifier="dummy_id",
            region_start=504.0,
            region_end=1000.0,
            region_area=0.13,
            relative_region_area=4.09,
            region_name="2",
            comment="Degraded",
            calculated_data=[
                CalculatedDocument(
                    uuid="dummy_id",
                    name="AverageSize",
                    value=395.0,
                    data_sources=[region_data_source],
                ),
                CalculatedDocument(
                    uuid="dummy_id",
                    name="Concentration",
                    value=1.11,
                    data_sources=[region_data_source],
                ),
            ],
        ),
    ]
