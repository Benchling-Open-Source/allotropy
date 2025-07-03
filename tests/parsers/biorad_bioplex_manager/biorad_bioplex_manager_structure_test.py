from unittest import mock
from xml.etree import ElementTree

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Analyte,
    Error,
)
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure import (
    AnalyteMetadata,
    create_analyte,
    SampleMetadata,
    SystemMetadata,
    Well,
)


def test_create_analyte_metadata() -> None:
    analyte_xml_string = """
    <MWAnalyte RegionNumber="18">
        <AnalyteName>Pn4</AnalyteName>
        <Reading Valid="true" Code="0" OutlierType="None">7.00000000000000000E+000</Reading>
    </MWAnalyte>
    """
    analyte_xml = ElementTree.fromstring(analyte_xml_string)  # noqa: S314
    analyte_metadata = AnalyteMetadata.create(analyte_xml)
    assert analyte_metadata == AnalyteMetadata(name="Pn4", region=18, error_msg=None)
    assert analyte_metadata.error is None


def test_create_analyte_sample_with_error() -> None:
    analyte_xml_string = """
    <MWAnalyte RegionNumber="18">
        <AnalyteName>Pn4</AnalyteName>
        <Reading Valid="true" Code="1" OutlierType="None">7.00000000000000000E+000</Reading>
    </MWAnalyte>
    """
    analyte_xml = ElementTree.fromstring(analyte_xml_string)  # noqa: S314
    analyte_metadata = AnalyteMetadata.create(analyte_xml)
    assert analyte_metadata.error_msg == "Low bead number"
    assert analyte_metadata.error == Error(error="Low bead number", feature="Pn4")


def test_create_well() -> None:
    test_filepath = (
        "tests/parsers/biorad_bioplex_manager/testdata/exclude/well_xml_example.xml"
    )
    tree = ElementTree.parse(test_filepath)  # noqa: S314
    well_xml = tree.getroot()
    well = Well.create(well_xml)

    assert well == Well(
        name="A1",
        sample_volume_setting=50,
        detector_gain_setting="2198",
        minimum_assay_bead_count_setting=25,
        well_total_events=717,
        acquisition_time="2023-05-09T18:55:02Z",
        analyst="baz",
        xml=well_xml,
    )


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
    bead_xml = ElementTree.fromstring(bead_xml_string)  # noqa: S314

    with mock.patch(
        "allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure.random_uuid_str",
        return_value="dummy_id",
    ):
        analyte_document_data = create_analyte(
            bead_xml,
            analyte_region_dict=analyte_region_dict,
        )
    assert analyte_document_data == Analyte(
        identifier="dummy_id",
        name="Pn4",
        fluorescence=992.5,
        assay_bead_count=46,
        assay_bead_identifier="62",
        statistic_datum_role=TStatisticDatumRole.median_role,
    )


def test_create_sample() -> None:
    sample_metadata = """
<Blank>
<Description>BLANK</Description><Label>B</Label>
<Dilution>1.00000000000000000E+000</Dilution>
</Blank>
    """
    sample_metadata_xml = ElementTree.fromstring(sample_metadata)  # noqa: S314
    member_well = """
<MemberWell RowNo="1" ColNo="12" WellNumber="12">
    <MWAnalytes>
        <MWAnalyte RegionNumber="12">
            <AnalyteName>alpha</AnalyteName>
            <Reading Valid="true" Code="0" OutlierType="None">2.91000000000000000E+002</Reading>
            <MWObsConc ReadingOK="false" ReadError="Data field has not been set" ReadErrorCode="9" RecoveryRange="NotInRange" RecoveryRangeCode="9">0.00000000000000000E+000</MWObsConc>
        </MWAnalyte>
        <MWAnalyte RegionNumber="15">
            <AnalyteName>bravo</AnalyteName>
            <Reading Valid="true" Code="0" OutlierType="None">1.17100000000000000E+003</Reading>
            <MWObsConc ReadingOK="false" ReadError="Data field has not been set" ReadErrorCode="9" RecoveryRange="NotInRange" RecoveryRangeCode="9">0.00000000000000000E+000</MWObsConc>
        </MWAnalyte>
    </MWAnalytes>
</MemberWell>
"""
    member_well_xml = ElementTree.fromstring(member_well)  # noqa: S314
    assert SampleMetadata.create(
        sample_metadata_xml, member_well_xml
    ) == SampleMetadata(
        sample_type=SampleRoleType.blank_role,
        sample_identifier="B",
        description="BLANK",
        errors=[],
        sample_dilution=1.0,
        analyte_region_dict={
            "12": "alpha",
            "15": "bravo",
        },
    )


def test_create_samples() -> None:
    test_filepath = (
        "tests/parsers/biorad_bioplex_manager/testdata/exclude/sample_xml_example.xml"
    )
    tree = ElementTree.parse(test_filepath)  # noqa: S314
    sample_xml = tree.getroot()
    samples = SampleMetadata.create_samples(sample_xml)
    assert isinstance(samples, dict)

    assert samples == {
        "A12": SampleMetadata(
            sample_type=SampleRoleType.blank_role,
            sample_identifier="B",
            description=None,
            errors=[],
            sample_dilution=None,
            analyte_region_dict={
                "12": "alpha",
            },
        ),
        "B12": SampleMetadata(
            sample_type=SampleRoleType.blank_role,
            sample_identifier="B",
            description=None,
            errors=[],
            sample_dilution=None,
            analyte_region_dict={
                "12": "alpha",
            },
        ),
        "C1": SampleMetadata(
            sample_type=SampleRoleType.control_sample_role,
            sample_identifier="C1",
            description=None,
            errors=[],
            sample_dilution=1.0,
            analyte_region_dict={
                "12": "alpha",
                "15": "bravo",
            },
        ),
        "C2": SampleMetadata(
            sample_type=SampleRoleType.control_sample_role,
            sample_identifier="C2",
            description=None,
            errors=[],
            sample_dilution=1.0,
            analyte_region_dict={
                "12": "alpha",
            },
        ),
        "D2": SampleMetadata(
            sample_type=SampleRoleType.control_sample_role,
            sample_identifier="C2",
            description=None,
            errors=[],
            sample_dilution=1.0,
            analyte_region_dict={
                "12": "alpha",
            },
        ),
    }


def test_create_system_metadata() -> None:
    test_filepath = (
        "tests/parsers/biorad_bioplex_manager/testdata/exclude/well_xml_example.xml"
    )
    tree = ElementTree.parse(test_filepath)  # noqa: S314
    well_system_xml = tree.getroot()
    assert SystemMetadata.create(well_system_xml) == SystemMetadata(
        plate_id="555",
        serial_number="LX12345678912",
        controller_version="2.6.1",
        analytical_method=r"Z:\corge\quux_qux Luminex\Protocols\qux_15PLEX_ASSAY.spbx",
        regions_of_interest=[
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
        ],
    )
