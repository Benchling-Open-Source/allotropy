from unittest import mock

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Analyte,
    Error,
    StatisticDimension,
    StatisticsDocument,
)
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure import (
    AnalyteMetadata,
    create_analyte,
    SampleMetadata,
    SystemMetadata,
    Well,
)
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement


def test_create_analyte_metadata() -> None:
    analyte_xml_string = """
    <MWAnalyte RegionNumber="18">
        <AnalyteName>Pn4</AnalyteName>
        <Reading Valid="true" Code="0" OutlierType="None">7.00000000000000000E+000</Reading>
    </MWAnalyte>
    """
    analyte_xml = StrictXmlElement.create_from_bytes(analyte_xml_string.encode("utf-8"))
    analyte_metadata = AnalyteMetadata.create(analyte_xml)
    assert analyte_metadata == AnalyteMetadata(
        name="Pn4", region=18, error_msg=None, custom_info={}
    )
    assert analyte_metadata.error is None


def test_create_analyte_sample_with_error() -> None:
    analyte_xml_string = """
    <MWAnalyte RegionNumber="18">
        <AnalyteName>Pn4</AnalyteName>
        <Reading Valid="true" Code="1" OutlierType="None">7.00000000000000000E+000</Reading>
    </MWAnalyte>
    """
    analyte_xml = StrictXmlElement.create_from_bytes(analyte_xml_string.encode("utf-8"))
    analyte_metadata = AnalyteMetadata.create(analyte_xml)
    assert analyte_metadata.error_msg == "Low bead number"
    assert analyte_metadata.error == Error(error="Low bead number", feature="Pn4")


def test_create_well() -> None:
    test_filepath = (
        "tests/parsers/biorad_bioplex_manager/testdata/exclude/well_xml_example.xml"
    )
    with open(test_filepath, "rb") as f:
        well_xml = StrictXmlElement.create_from_bytes(f.read())
    well = Well.create(well_xml)

    assert well == Well(
        name="A1",
        sample_volume_setting=50,
        detector_gain_setting="2198",
        minimum_assay_bead_count_setting=25,
        well_total_events=717,
        acquisition_time="2023-05-09T18:55:02Z",
        analyst="baz",
        xml=well_xml.element,
        custom_info={
            "ColNo": "1",
            "PlateID": "555",
            "RowNo": "1",
            "RunProtocolDocumentLocation": "Z:\\corge\\quux_qux Luminex\\Protocols\\qux_15PLEX_ASSAY.spbx",
            "RunProtocolDocumentName": "qux_15PLEX_ASSAY",
            "TotalGatedEvents": "637",
            "TotalRegionEventCount": "609",
            "WellNo": "1",
        },
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
    bead_xml = StrictXmlElement.create_from_bytes(bead_xml_string.encode("utf-8"))

    with mock.patch(
        "allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure.random_uuid_str",
        return_value="dummy_id",
    ):
        analyte_document_data = create_analyte(
            bead_xml,
            analyte_region_dict=analyte_region_dict,
        )

    # Expected statistics from the XML
    expected_statistics = [
        StatisticsDocument(
            statistical_feature="fluorescence",
            statistic_dimensions=[
                StatisticDimension(
                    value=992.5,
                    unit="RFU",
                    statistic_datum_role=TStatisticDatumRole.median_role,
                ),
                StatisticDimension(
                    value=983.391296386718750,
                    unit="RFU",
                    statistic_datum_role=TStatisticDatumRole.arithmetic_mean_role,
                ),
                StatisticDimension(
                    value=0.223858922719955440,
                    unit="(unitless)",
                    statistic_datum_role=TStatisticDatumRole.coefficient_of_variation_role,
                ),
                StatisticDimension(
                    value=220.140914916992190,
                    unit="(unitless)",
                    statistic_datum_role=TStatisticDatumRole.standard_deviation_role,
                ),
                StatisticDimension(
                    value=974.904785156250000,
                    unit="RFU",
                    statistic_datum_role=TStatisticDatumRole.trimmed_arithmetic_mean_role,
                ),
                StatisticDimension(
                    value=181.356109619140620,
                    unit="(unitless)",
                    statistic_datum_role=TStatisticDatumRole.trimmed_standard_deviation_role,
                ),
            ],
        )
    ]

    assert analyte_document_data == Analyte(
        identifier="dummy_id",
        name="Pn4",
        assay_bead_count=46,
        assay_bead_identifier="62",
        statistics=expected_statistics,
        custom_info={
            "StdErr": "3.24580078125000000E+001",
            "TrimmedCV": "1.86024442315101620E-001",
        },
    )


def test_create_sample() -> None:
    sample_metadata = """
<Blank>
<Description>BLANK</Description><Label>B</Label>
<Dilution>1.00000000000000000E+000</Dilution>
</Blank>
    """
    sample_metadata_xml = StrictXmlElement.create_from_bytes(
        sample_metadata.encode("utf-8")
    )
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
    member_well_xml = StrictXmlElement.create_from_bytes(member_well.encode("utf-8"))
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
        custom_info={"ColNo": "12", "RowNo": "1", "WellNumber": "12"},
    )


def test_create_samples() -> None:
    test_filepath = (
        "tests/parsers/biorad_bioplex_manager/testdata/exclude/sample_xml_example.xml"
    )
    with open(test_filepath, "rb") as f:
        sample_xml = StrictXmlElement.create_from_bytes(f.read())
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
            custom_info={"ColNo": "12", "RowNo": "1", "WellNumber": "12"},
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
            custom_info={"ColNo": "12", "RowNo": "2", "WellNumber": "24"},
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
            custom_info={"ColNo": "1", "RowNo": "3", "WellNumber": "25"},
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
            custom_info={"ColNo": "2", "RowNo": "3", "WellNumber": "26"},
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
            custom_info={"ColNo": "2", "RowNo": "4", "WellNumber": "38"},
        ),
    }


def test_create_system_metadata() -> None:
    test_filepath = (
        "tests/parsers/biorad_bioplex_manager/testdata/exclude/well_xml_example.xml"
    )
    with open(test_filepath, "rb") as f:
        well_system_xml = StrictXmlElement.create_from_bytes(f.read())
    assert SystemMetadata.create(well_system_xml) == SystemMetadata(
        plate_id="555",
        serial_number="LX12345678912",
        controller_version="2.6.1",
        analytical_method=r"Z:\corge\quux_qux Luminex\Protocols\qux_15PLEX_ASSAY.spbx",
        custom_info={
            "AcquisitionTime": "2023-05-09T18:55:02Z",
            "ColNo": "1",
            "RowNo": "1",
            "RunProtocolDocumentName": "qux_15PLEX_ASSAY",
            "TotalEvents": "717",
            "TotalGatedEvents": "637",
            "TotalRegionEventCount": "609",
            "User": "baz",
            "WellNo": "1",
        },
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
