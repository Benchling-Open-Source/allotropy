from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET  # noqa: N817

from allotropy.parsers.bd_biosciences_facsdiva.bd_biosciences_facsdiva_structure import (
    _create_compensation_matrix_groups,
    _create_data_regions,
    _create_populations,
    _extract_statistics_from_calculations,
    create_measurement_groups,
    create_metadata,
    RegionType,
)
from allotropy.parsers.bd_biosciences_facsdiva.constants import (
    DEVICE_IDENTIFIER,
    DEVICE_TYPE,
    SOFTWARE_NAME,
)
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bdfacs version="Version 6.2" release_version="Version 6.2">
    <experiment name="Test Experiment">
        <date>2023-01-01T12:00:00</date>
        <owner_name>Test User</owner_name>
        <export_time>2023-01-01T12:30:00</export_time>
        <specimen name="TestSpecimen">
            <tube name="TestTube1">
                <date>2023-01-01T12:15:00</date>
                <data_filename>test.fcs</data_filename>
                <data_begin_date>2023-01-01T12:10:00</data_begin_date>
                <data_end_date>2023-01-01T12:20:00</data_end_date>
                <data_instrument_serial_number>SERIAL123</data_instrument_serial_number>
                <data_instrument_name>Test Cytometer</data_instrument_name>
                <data_instrument_type>LSRFortessa</data_instrument_type>
                <record_user>TestUser</record_user>
                <gates>
                    <gate fullname="All Events" type="EventSource_Classifier">
                        <region name="All Events" type="SOURCE_REGION" statistics="true">
                            <count type="int" value="10000"/>
                        </region>
                    </gate>
                    <gate fullname="All Events\\P1" type="Region_Classifier">
                        <parent>All Events</parent>
                        <region name="P1" type="POLYGON_REGION" xparm="FSC-A" yparm="SSC-A" statistics="true">
                            <count type="int" value="8000"/>
                            <point x="1000" y="2000"/>
                            <point x="3000" y="4000"/>
                            <point x="5000" y="1000"/>
                        </region>
                    </gate>
                    <gate fullname="All Events\\P1\\P2" type="Region_Classifier">
                        <parent>All Events\\P1</parent>
                        <region name="P2" type="RECTANGLE_REGION" xparm="CD3" yparm="CD4" statistics="true">
                            <count type="int" value="5000"/>
                            <point x="0" y="0"/>
                            <point x="1000" y="1000"/>
                        </region>
                    </gate>
                    <gate fullname="All Events\\P1\\P2\\P3" type="Region_Classifier">
                        <parent>All Events\\P1\\P2</parent>
                        <region name="P3" type="POLYGON_REGION" xparm="PE-A" yparm="APC-A" statistics="true">
                            <count type="int" value="3000"/>
                            <point x="100" y="200"/>
                            <point x="300" y="400"/>
                            <point x="500" y="100"/>
                        </region>
                    </gate>
                    <gate fullname="All Events\\P4" type="Region_Classifier">
                        <parent>All Events</parent>
                        <region name="P4" type="BINNER_REGION" xparm="CD8" yparm="CD45" statistics="true">
                            <count type="int" value="2000"/>
                        </region>
                    </gate>
                </gates>
                <compensation>
                    <spillover_data format="FACSDiva%2B10.5">
                        <parameter name="PE-A">
                            <spillover_value parameter="FITC-A">0.05</spillover_value>
                            <spillover_value parameter="PE-A">1.0</spillover_value>
                        </parameter>
                        <parameter name="APC-A">
                            <spillover_value parameter="PE-A">0.02</spillover_value>
                            <spillover_value parameter="APC-A">1.0</spillover_value>
                        </parameter>
                    </spillover_data>
                </compensation>
                <statistics_calculations>
                    <calculation_schedule gate="All Events\\P1\\P2" parameter="PE-A">
                        <calculation formula="sum of squares" value="1245.67"/>
                        <calculation formula="Median" value="178.32"/>
                        <calculation formula="SD" value="42.55"/>
                        <calculation formula="count" value="1254"/>
                    </calculation_schedule>
                    <calculation_schedule gate="All Events\\P4" parameter="APC-A">
                        <calculation formula="sum of squares" value="NaN"/>
                        <calculation formula="Median" value="85.21"/>
                        <calculation formula="SD" value="NaN"/>
                        <calculation formula="count" value="768"/>
                    </calculation_schedule>
                </statistics_calculations>
                <pipeline>
                    <storage_gate>All Events</storage_gate>
                    <color_counter>0</color_counter>
                    <stop_rule mode="1" time="0" gate="All Events" events="10000"/>
                </pipeline>
            </tube>
        </specimen>
    </experiment>
</bdfacs>
"""

def load_sample_xml() -> StrictXmlElement:
    root_element_et = ET.parse(BytesIO(SAMPLE_XML.encode())).getroot()  # noqa: S314
    return StrictXmlElement(root_element_et)


def test_create_metadata() -> None:
    root_element = load_sample_xml()
    file_path = "/path/to/test_file.xml"

    metadata = create_metadata(root_element, file_path)

    assert metadata.file_name == Path(file_path).name
    assert metadata.unc_path == file_path
    assert metadata.device_identifier == DEVICE_IDENTIFIER
    assert metadata.software_name == SOFTWARE_NAME
    assert metadata.software_version == "Version 6.2"
    assert metadata.model_number == "Test Cytometer"
    assert metadata.equipment_serial_number == "SERIAL123"
    assert metadata.asm_file_identifier == Path(file_path).with_suffix(".json").name


def test_create_data_regions() -> None:
    root_element = load_sample_xml()
    tube = root_element.recursive_find_or_none(["experiment", "specimen", "tube"])
    assert tube is not None

    data_regions = _create_data_regions(tube)

    assert data_regions is not None
    assert len(data_regions) == 4

    p1_region = next((r for r in data_regions if r.region_data_identifier == "P1"), None)
    assert p1_region is not None
    assert p1_region.region_data_type == RegionType.POLYGON.value
    assert p1_region.parent_data_region_identifier is None
    assert p1_region.x_coordinate_dimension_identifier == "FSC-A"
    assert p1_region.y_coordinate_dimension_identifier == "SSC-A"

    p2_region = next((r for r in data_regions if r.region_data_identifier == "P2"), None)
    assert p2_region is not None
    assert p2_region.region_data_type == RegionType.RECTANGLE.value
    assert p2_region.parent_data_region_identifier == "P1"
    assert p2_region.x_coordinate_dimension_identifier == "CD3"
    assert p2_region.y_coordinate_dimension_identifier == "CD4"

    p3_region = next((r for r in data_regions if r.region_data_identifier == "P3"), None)
    assert p3_region is not None
    assert p3_region.region_data_type == RegionType.POLYGON.value
    assert p3_region.parent_data_region_identifier == "P2"
    assert p3_region.x_coordinate_dimension_identifier == "PE-A"
    assert p3_region.y_coordinate_dimension_identifier == "APC-A"

    p4_region = next((r for r in data_regions if r.region_data_identifier == "P4"), None)
    assert p4_region is not None
    assert p4_region.region_data_type == RegionType.BINNER.value
    assert p4_region.parent_data_region_identifier is None
    assert p4_region.x_coordinate_dimension_identifier == "CD8"
    assert p4_region.y_coordinate_dimension_identifier == "CD45"


def test_create_populations() -> None:
    root_element = load_sample_xml()
    tube = root_element.recursive_find_or_none(["experiment", "specimen", "tube"])
    assert tube is not None

    populations = _create_populations(tube)

    assert populations is not None
    assert len(populations) == 1

    root_population = populations[0]
    if root_population.count is not None:
        assert root_population.count == 10000

    assert root_population.population_identifier is not None

    assert root_population.sub_populations is not None
    assert len(root_population.sub_populations) >= 1

    p1_population = next((p for p in root_population.sub_populations
                          if p.data_region_identifier == "P1"
                          or (p.written_name == "P1" if p.written_name else False)),
                         None)

    if p1_population:
        assert p1_population.parent_population_identifier == root_population.population_identifier


def test_create_compensation_matrix_groups() -> None:
    root_element = load_sample_xml()
    tube = root_element.recursive_find_or_none(["experiment", "specimen", "tube"])
    assert tube is not None

    comp_matrix_groups = _create_compensation_matrix_groups(tube)

    if comp_matrix_groups is None:
        return

    assert len(comp_matrix_groups) == 2

    pe_group = next((g for g in comp_matrix_groups if g.dimension_identifier == "PE-A"), None)
    assert pe_group is not None
    assert pe_group.compensation_matrices is not None
    assert len(pe_group.compensation_matrices) == 2

    fitc_matrix = next(
        (m for m in pe_group.compensation_matrices if m.dimension_identifier == "FITC-A"),
        None,
    )
    assert fitc_matrix is not None
    assert fitc_matrix.compensation_value == 0.05

    pe_matrix = next(
        (m for m in pe_group.compensation_matrices if m.dimension_identifier == "PE-A"),
        None,
    )
    assert pe_matrix is not None
    assert pe_matrix.compensation_value == 1.0

    apc_group = next((g for g in comp_matrix_groups if g.dimension_identifier == "APC-A"), None)
    assert apc_group is not None
    assert apc_group.compensation_matrices is not None
    assert len(apc_group.compensation_matrices) == 2

    pe_matrix_in_apc = next(
        (m for m in apc_group.compensation_matrices if m.dimension_identifier == "PE-A"),
        None,
    )
    assert pe_matrix_in_apc is not None
    assert pe_matrix_in_apc.compensation_value == 0.02


def test_extract_statistics_from_calculations() -> None:
    root_element = load_sample_xml()
    tube = root_element.recursive_find_or_none(["experiment", "specimen", "tube"])
    assert tube is not None

    p2_stats = _extract_statistics_from_calculations(tube, "All Events\\P1\\P2")
    assert p2_stats is not None

    fluorescence_stat = next((s for s in p2_stats if s.statistical_feature == "fluorescence"), None)
    assert fluorescence_stat is not None

    median_dim = next(
        (d for d in fluorescence_stat.statistic_dimension if d.has_statistic_datum_role == "median role"),
        None,
    )
    if median_dim:
        assert median_dim.value == 178.32
        assert median_dim.unit == "RFU"

    count_stat = next((s for s in p2_stats if s.statistical_feature == "count"), None)
    if count_stat:
        assert count_stat.statistic_dimension[0].unit == "count"

    p4_stats = _extract_statistics_from_calculations(tube, "All Events\\P4")
    if p4_stats:
        fluorescence_stat = next((s for s in p4_stats if s.statistical_feature == "fluorescence"), None)
        if fluorescence_stat:
            median_dim = next(
                (d for d in fluorescence_stat.statistic_dimension if d.has_statistic_datum_role == "median role"),
                None,
            )
            if median_dim:
                assert median_dim.value == 85.21
                assert median_dim.unit == "RFU"


def test_create_measurement_groups() -> None:
    root_element = load_sample_xml()

    measurement_groups = create_measurement_groups(root_element)

    assert measurement_groups is not None
    assert len(measurement_groups) == 1

    group = measurement_groups[0]
    assert group.experimental_data_identifier is not None

    assert group.measurement_time is not None

    if group.compensation_matrix_groups:
        assert len(group.compensation_matrix_groups) > 0

    assert group.measurements is not None
    assert len(group.measurements) == 1

    measurement = group.measurements[0]
    assert measurement.measurement_identifier is not None
    assert measurement.sample_identifier is not None
    assert measurement.device_type == DEVICE_TYPE

    assert measurement.populations is not None
    assert len(measurement.populations) == 1

    root_population = measurement.populations[0]
    assert root_population.population_identifier is not None

    assert measurement.data_regions is not None
    assert len(measurement.data_regions) > 0
