from xml.etree import ElementTree

import pytest

from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure import (
    AnalyteDocumentData,
    AnalyteSample,
    DeviceWellSettings,
    SampleDocumentAggregate,
    validate_xml_structure,
    WellSystemLevelMetadata,
)


@pytest.mark.short
def test_create_analyte_sample() -> None:
    analyte_xml_string = """
    <MWAnalyte RegionNumber="18">
        <AnalyteName>Pn4</AnalyteName>
        <Reading Valid="true" Code="0" OutlierType="None">7.00000000000000000E+000</Reading>
    </MWAnalyte>
    """
    analyte_name = "Pn4"
    analyte_xml = ElementTree.fromstring(analyte_xml_string)  # noqa: S314
    analyte_sample = AnalyteSample.create(analyte_xml)
    assert analyte_sample.analyte_name == analyte_name
    assert analyte_sample.analyte_region == 18
    assert analyte_sample.analyte_error_code == "0"


@pytest.mark.short
def test_create_device_settings() -> None:
    test_filepath = (
        "tests/parsers/biorad_bioplex_manager/testdata/exclude/well_xml_example.xml"
    )
    tree = ElementTree.parse(test_filepath)  # noqa: S314
    well_settings_xml = tree.getroot()
    well_settings = DeviceWellSettings.create(well_settings_xml)

    assert well_settings.well_name == "A1"
    assert well_settings.detector_gain_setting == "2198"
    assert well_settings.sample_volume_setting == 50


@pytest.mark.short
def test_create_analyte_document_data() -> None:
    bead_xml_string = """
                    <BeadRegion RegionNumber="62">
                    <RegionCount>46</RegionCount>
                    <Median>992.50</Median>
                    <Mean>9.83391296386718750E+002</Mean>
                    <CV>2.23858922719955440E-001</CV>
                    <StdDev>2.20140914916992190E+002</StdDev>
                    <StdErr>3.24580078125000000E+001</StdErr>
                    <TrimmedMean>9.74904785156250000E+002</TrimmedMean>
                    <TrimmedCV>1.86024442315101620E-001</TrimmedCV>
                    <TrimmedStdDev>1.81356109619140620E+002</TrimmedStdDev>
                </BeadRegion>
                """
    analyte_region_dict = {"62": "Pn4"}
    regions_of_interest = ["62"]
    analyte_doc_data_expected = AnalyteDocumentData(
        analyte_name="Pn4",
        assay_bead_count=46,
        assay_bead_identifier="62",
        fluorescence=992.5,
    )
    bead_xml = ElementTree.fromstring(bead_xml_string)  # noqa: S314
    analyte_document_data = AnalyteDocumentData.create(
        bead_xml,
        analyte_region_dict=analyte_region_dict,
        regions_of_interest=regions_of_interest,
    )
    if analyte_document_data is not None:
        assert analyte_document_data == analyte_doc_data_expected


def test_sample_aggregate_doc() -> None:
    test_filepath = "tests/parsers/biorad_bioplex_manager/testdata/bio-rad_bio-plex_manager_example_01.xml"
    tree = ElementTree.parse(test_filepath)  # noqa: S314
    root = tree.getroot()
    for child in root:
        if child.tag == "Samples":
            sample_aggregate_doc = SampleDocumentAggregate.create(child)
    assert isinstance(sample_aggregate_doc, SampleDocumentAggregate)
    assert isinstance(sample_aggregate_doc.samples_dict, dict)
    assert isinstance(sample_aggregate_doc.analyte_region_dict, dict)


@pytest.mark.short
def test_well_sytem_level_metadata() -> None:
    test_filepath = (
        "tests/parsers/biorad_bioplex_manager/testdata/exclude/well_xml_example.xml"
    )
    tree = ElementTree.parse(test_filepath)  # noqa: S314
    well_system_xml = tree.getroot()
    well_system = WellSystemLevelMetadata.create(well_system_xml)

    assert well_system.plate_id == "555"
    assert well_system.serial_number == "LX12345678912"
    assert well_system.controller_version == "2.6.1"
    assert well_system.user == "baz"
    assert (
        well_system.analytical_method
        == r"Z:\corge\quux_qux Luminex\Protocols\qux_15PLEX_ASSAY.spbx"
    )
    assert well_system.regions_of_interest == [
        "12",
        "15",
        "18",
        "21",
        "25",
        "28",
        "33",
        "36",
        "42",
        "47",
        "53",
        "57",
        "62",
        "67",
        "75",
    ]


@pytest.mark.short
def test_validate_xml_structure() -> None:
    test_filepath = "tests/parsers/biorad_bioplex_manager/testdata/bio-rad_bio-plex_manager_example_01.xml"
    tree = ElementTree.parse(test_filepath)  # noqa: S314
    root = tree.getroot()
    try:
        validate_xml_structure(root)
    except Exception as e:
        pytest.fail(f"Function raised an exception: {e}")
