from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET  # noqa: N817

from allotropy.parsers.flowjo.constants import (
    DEVICE_IDENTIFIER,
    DEVICE_TYPE,
    SOFTWARE_NAME,
)
from allotropy.parsers.flowjo.flowjo_structure import (
    _create_compensation_matrix_groups,
    _create_data_regions,
    _create_populations,
    _extract_dimension_identifiers,
    _extract_vertices,
    _get_file_path,
    _get_gate_type,
    _get_keyword_value_by_name_from_sample,
    _get_measurement_time,
    _process_sample,
    create_measurement_groups,
    create_metadata,
    RegionType,
    VertexRole,
)
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement

# Sample XML string for testing without file dependency
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Workspace xmlns:gating="http://www.isac-net.org/std/Gating-ML/v2.0/gating"
           xmlns:transforms="http://www.isac-net.org/std/Gating-ML/v2.0/transformations"
           xmlns:data-type="http://www.isac-net.org/std/Gating-ML/v2.0/datatypes"
           version="1.0" flowJoVersion="10.8.1">
  <SampleList>
    <Sample>
      <Keywords>
        <Keyword name="$DATE" value="01-Jan-2023"/>
        <Keyword name="$ETIM" value="12:00:00"/>
        <Keyword name="$CYTSN" value="SERIAL123"/>
      </Keywords>
      <SampleNode name="Test_Sample" count="10000" sampleID="123">
        <Subpopulations>
          <Population name="Lymphocytes" count="5000">
            <Gate gating:id="ID123">
              <gating:PolygonGate eventsInside="1">
                <gating:dimension>
                  <data-type:fcs-dimension data-type:name="FSC-A"/>
                </gating:dimension>
                <gating:dimension>
                  <data-type:fcs-dimension data-type:name="SSC-A"/>
                </gating:dimension>
                <gating:vertex>
                  <gating:coordinate data-type:value="100.0"/>
                  <gating:coordinate data-type:value="200.0"/>
                </gating:vertex>
                <gating:vertex>
                  <gating:coordinate data-type:value="300.0"/>
                  <gating:coordinate data-type:value="400.0"/>
                </gating:vertex>
                <gating:vertex>
                  <gating:coordinate data-type:value="500.0"/>
                  <gating:coordinate data-type:value="600.0"/>
                </gating:vertex>
              </gating:PolygonGate>
            </Gate>
            <Subpopulations>
              <Population name="T Cells" count="3000">
                <Gate gating:id="ID456" gating:parent_id="ID123">
                  <gating:RectangleGate eventsInside="1">
                    <gating:dimension gating:min="0" gating:max="1000">
                      <data-type:fcs-dimension data-type:name="CD3"/>
                    </gating:dimension>
                    <gating:dimension gating:min="0" gating:max="1000">
                      <data-type:fcs-dimension data-type:name="CD4"/>
                    </gating:dimension>
                  </gating:RectangleGate>
                </Gate>
              </Population>
              <Population name="Ellipsoid Population" count="2000">
                <Gate gating:id="ID789" gating:parent_id="ID456">
                  <gating:EllipsoidGate eventsInside="1" gating:distance="55.631724741469334">
                    <gating:dimension>
                      <data-type:fcs-dimension data-type:name="Comp-PE-A" />
                    </gating:dimension>
                    <gating:dimension>
                      <data-type:fcs-dimension data-type:name="Comp-BV786-A" />
                    </gating:dimension>
                    <gating:foci>
                      <gating:vertex>
                        <gating:coordinate data-type:value="57.89" />
                        <gating:coordinate data-type:value="94.97" />
                      </gating:vertex>
                      <gating:vertex>
                        <gating:coordinate data-type:value="98.10" />
                        <gating:coordinate data-type:value="74.02" />
                      </gating:vertex>
                    </gating:foci>
                    <gating:edge>
                      <gating:vertex>
                        <gating:coordinate data-type:value="54" />
                        <gating:coordinate data-type:value="97" />
                      </gating:vertex>
                      <gating:vertex>
                        <gating:coordinate data-type:value="102" />
                        <gating:coordinate data-type:value="72" />
                      </gating:vertex>
                    <gating:vertex>
                        <gating:coordinate data-type:value="36" />
                        <gating:coordinate data-type:value="22" />
                      </gating:vertex>
                      <gating:vertex>
                        <gating:coordinate data-type:value="22" />
                        <gating:coordinate data-type:value="92" />
                      </gating:vertex>
                    </gating:edge>
                  </gating:EllipsoidGate>
                </Gate>
              </Population>
              <Population name="CurlyQuad Population" count="1500">
                <Gate gating:id="ID987" gating:parent_id="ID456">
                  <gating:CurlyQuad eventsInside="1">
                    <gating:dimension gating:min="100" gating:max="900">
                      <data-type:fcs-dimension data-type:name="CD8"/>
                    </gating:dimension>
                    <gating:dimension gating:min="200" gating:max="800">
                      <data-type:fcs-dimension data-type:name="CD45"/>
                    </gating:dimension>
                  </gating:CurlyQuad>
                </Gate>
              </Population>
            </Subpopulations>
          </Population>
        </Subpopulations>
      </SampleNode>
      <transforms:spilloverMatrix>
        <transforms:spillover data-type:parameter="PE-A">
          <transforms:coefficient data-type:parameter="FITC-A" transforms:value="0.05"/>
          <transforms:coefficient data-type:parameter="PE-A" transforms:value="1.0"/>
        </transforms:spillover>
      </transforms:spilloverMatrix>
    </Sample>
  </SampleList>
  <Cytometers>
    <Cytometer cyt="Test Cytometer"/>
  </Cytometers>
</Workspace>
"""


def load_sample_xml() -> StrictXmlElement:
    root_element_et = ET.parse(BytesIO(SAMPLE_XML.encode())).getroot()  # noqa: S314

    namespaces = {
        "transforms": "http://www.isac-net.org/std/Gating-ML/v2.0/transformations",
        "data-type": "http://www.isac-net.org/std/Gating-ML/v2.0/datatypes",
        "gating": "http://www.isac-net.org/std/Gating-ML/v2.0/gating",
    }

    return StrictXmlElement(root_element_et, namespaces)


def test_get_file_path() -> None:
    assert _get_file_path("path/to/file.txt") == "file.txt"
    assert _get_file_path(None) is None


def test_create_metadata() -> None:
    root_element = load_sample_xml()
    file_path = "/path/to/test_file.wsp"

    metadata = create_metadata(root_element, file_path)

    assert metadata.file_name == Path(file_path).name
    assert metadata.unc_path == file_path
    assert metadata.device_identifier == DEVICE_IDENTIFIER
    assert metadata.software_name == SOFTWARE_NAME
    assert metadata.software_version == "10.8.1"
    assert metadata.model_number == "Test Cytometer"
    assert metadata.asm_file_identifier == Path(file_path).with_suffix(".json").name


def test_get_keyword_value_by_name_from_sample() -> None:
    root_element = load_sample_xml()
    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    date_value = _get_keyword_value_by_name_from_sample(sample, "$DATE")
    assert date_value == "01-Jan-2023"

    time_value = _get_keyword_value_by_name_from_sample(sample, "$ETIM")
    assert time_value == "12:00:00"

    serial_value = _get_keyword_value_by_name_from_sample(sample, "$CYTSN")
    assert serial_value == "SERIAL123"

    nonexistent_value = _get_keyword_value_by_name_from_sample(
        sample, "NONEXISTENT_KEYWORD"
    )
    assert nonexistent_value is None


def test_get_measurement_time() -> None:
    root_element = load_sample_xml()
    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    measurement_time = _get_measurement_time(sample)
    assert measurement_time == "01-Jan-2023 12:00:00"
    assert " " in measurement_time


def test_process_sample() -> None:
    root_element = load_sample_xml()
    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    populations = _process_sample(sample)

    assert populations is not None
    assert len(populations) == 1

    root_population = populations[0]
    assert root_population.parent_population_identifier is None
    assert root_population.written_name == "Test_Sample"
    assert root_population.count == 10000

    assert root_population.sub_populations is not None
    assert len(root_population.sub_populations) == 1

    lymphocytes = root_population.sub_populations[0]
    assert (
        lymphocytes.parent_population_identifier
        == root_population.population_identifier
    )
    assert lymphocytes.written_name == "Lymphocytes"
    assert lymphocytes.count == 5000

    assert lymphocytes.sub_populations is not None
    assert len(lymphocytes.sub_populations) == 3

    t_cells = lymphocytes.sub_populations[0]
    assert t_cells.parent_population_identifier == lymphocytes.population_identifier
    assert t_cells.written_name == "T Cells"
    assert t_cells.count == 3000


def test_create_populations() -> None:
    root_element = load_sample_xml()
    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    sample_node = sample.find_or_none("SampleNode")
    assert sample_node is not None

    subpops_element = sample_node.find_or_none("Subpopulations")
    assert subpops_element is not None

    populations = _create_populations(subpops_element)

    assert populations is not None
    assert len(populations) == 1

    lymphocytes = populations[0]
    assert lymphocytes.written_name == "Lymphocytes"
    assert lymphocytes.count == 5000
    assert lymphocytes.data_region_identifier == "ID123"

    assert lymphocytes.sub_populations is not None
    assert len(lymphocytes.sub_populations) == 3

    t_cells = lymphocytes.sub_populations[0]
    assert t_cells.written_name == "T Cells"
    assert t_cells.count == 3000
    assert t_cells.data_region_identifier == "ID456"
    assert t_cells.parent_population_identifier == lymphocytes.population_identifier


def test_create_data_regions() -> None:
    root_element = load_sample_xml()
    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    data_regions = _create_data_regions(sample)

    assert data_regions is not None
    assert len(data_regions) == 4

    lymphocyte_region = next(
        (r for r in data_regions if r.region_data_identifier == "ID123"), None
    )
    assert lymphocyte_region is not None
    assert lymphocyte_region.region_data_type == RegionType.POLYGON.value
    assert lymphocyte_region.parent_data_region_identifier is None
    assert lymphocyte_region.x_coordinate_dimension_identifier == "FSC-A"
    assert lymphocyte_region.y_coordinate_dimension_identifier == "SSC-A"

    t_cell_region = next(
        (r for r in data_regions if r.region_data_identifier == "ID456"), None
    )
    assert t_cell_region is not None
    assert t_cell_region.region_data_type == RegionType.RECTANGLE.value
    assert t_cell_region.parent_data_region_identifier == "ID123"
    assert t_cell_region.x_coordinate_dimension_identifier == "CD3"
    assert t_cell_region.y_coordinate_dimension_identifier == "CD4"

    ellipsoid_region = next(
        (r for r in data_regions if r.region_data_identifier == "ID789"), None
    )
    assert ellipsoid_region is not None
    assert ellipsoid_region.region_data_type == RegionType.ELLIPSOID.value
    assert ellipsoid_region.parent_data_region_identifier == "ID456"
    assert ellipsoid_region.x_coordinate_dimension_identifier == "Comp-PE-A"
    assert ellipsoid_region.y_coordinate_dimension_identifier == "Comp-BV786-A"

    curly_quad_region = next(
        (r for r in data_regions if r.region_data_identifier == "ID987"), None
    )
    assert curly_quad_region is not None
    assert curly_quad_region.region_data_type == RegionType.CURLY_QUAD.value
    assert curly_quad_region.parent_data_region_identifier == "ID456"
    assert curly_quad_region.x_coordinate_dimension_identifier == "CD8"
    assert curly_quad_region.y_coordinate_dimension_identifier == "CD45"


def test_create_compensation_matrix_groups() -> None:
    root_element = load_sample_xml()
    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    transform_matrix_element = sample.find_or_none("transforms:spilloverMatrix")
    assert transform_matrix_element is not None

    comp_matrix_groups = _create_compensation_matrix_groups(transform_matrix_element)

    assert comp_matrix_groups is not None
    assert len(comp_matrix_groups) == 1

    group = comp_matrix_groups[0]
    assert group.dimension_identifier == "PE-A"
    assert group.compensation_matrices is not None
    assert len(group.compensation_matrices) == 2

    fitc_matrix = next(
        (m for m in group.compensation_matrices if m.dimension_identifier == "FITC-A"),
        None,
    )
    assert fitc_matrix is not None
    assert fitc_matrix.compensation_value == 0.05

    pe_matrix = next(
        (m for m in group.compensation_matrices if m.dimension_identifier == "PE-A"),
        None,
    )
    assert pe_matrix is not None
    assert pe_matrix.compensation_value == 1.0


def test_get_gate_type() -> None:
    root_element = load_sample_xml()

    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    population = sample.recursive_find_or_none(
        ["SampleNode", "Subpopulations", "Population"]
    )
    assert population is not None

    gate = population.find_or_none("Gate")
    assert gate is not None

    gate_type = _get_gate_type(gate)
    assert gate_type == RegionType.POLYGON.value

    t_cell_population = population.recursive_find_or_none(
        ["Subpopulations", "Population"]
    )
    assert t_cell_population is not None

    t_cell_gate = t_cell_population.find_or_none("Gate")
    assert t_cell_gate is not None

    t_cell_gate_type = _get_gate_type(t_cell_gate)
    assert t_cell_gate_type == RegionType.RECTANGLE.value


def test_extract_dimension_identifiers() -> None:
    root_element = load_sample_xml()

    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    population = sample.recursive_find_or_none(
        ["SampleNode", "Subpopulations", "Population"]
    )
    assert population is not None

    gate = population.find_or_none("Gate")
    assert gate is not None

    polygon_gate = gate.find_or_none(f"gating:{RegionType.POLYGON.value}Gate")
    assert polygon_gate is not None

    x_dim, y_dim = _extract_dimension_identifiers(polygon_gate)

    assert x_dim == "FSC-A"
    assert y_dim == "SSC-A"

    # Get the rectangle gate
    t_cell_population = population.recursive_find_or_none(
        ["Subpopulations", "Population"]
    )
    assert t_cell_population is not None

    t_cell_gate = t_cell_population.find_or_none("Gate")
    assert t_cell_gate is not None

    rectangle_gate = t_cell_gate.find_or_none(
        f"gating:{RegionType.RECTANGLE.value}Gate"
    )
    assert rectangle_gate is not None

    x_dim, y_dim = _extract_dimension_identifiers(rectangle_gate)

    assert x_dim == "CD3"
    assert y_dim == "CD4"


def test_extract_vertices() -> None:
    root_element = load_sample_xml()

    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    population = sample.recursive_find_or_none(
        ["SampleNode", "Subpopulations", "Population"]
    )
    assert population is not None

    gate = population.find_or_none("Gate")
    assert gate is not None

    gate_type = _get_gate_type(gate)
    assert gate_type == RegionType.POLYGON.value

    polygon_gate = gate.find_or_none(f"gating:{RegionType.POLYGON.value}Gate")
    assert polygon_gate is not None

    vertices = _extract_vertices(polygon_gate, gate_type)

    assert vertices is not None
    assert len(vertices) == 3

    assert vertices[0].x_coordinate == 100.0
    assert vertices[0].y_coordinate == 200.0

    assert vertices[1].x_coordinate == 300.0
    assert vertices[1].y_coordinate == 400.0

    assert vertices[2].x_coordinate == 500.0
    assert vertices[2].y_coordinate == 600.0


def test_extract_vertices_rectangle() -> None:
    root_element = load_sample_xml()

    sample = root_element.recursive_find_or_none(["SampleList", "Sample"])
    assert sample is not None

    t_cell_population = sample.recursive_find_or_none(
        ["SampleNode", "Subpopulations", "Population", "Subpopulations", "Population"]
    )
    assert t_cell_population is not None

    gate = t_cell_population.find_or_none("Gate")
    assert gate is not None

    gate_type = _get_gate_type(gate)
    assert gate_type == RegionType.RECTANGLE.value

    rectangle_gate = gate.find_or_none(f"gating:{RegionType.RECTANGLE.value}Gate")
    assert rectangle_gate is not None

    vertices = _extract_vertices(rectangle_gate, gate_type)

    assert vertices is not None
    assert len(vertices) == 4  # Rectangle should have 4 vertices

    # Check for corners of the rectangle (0,0) to (1000,1000)
    corners = [(0.0, 0.0), (0.0, 1000.0), (1000.0, 1000.0), (1000.0, 0.0)]

    for i, (expected_x, expected_y) in enumerate(corners):
        x_coordinate = vertices[i].x_coordinate
        y_coordinate = vertices[i].y_coordinate
        assert x_coordinate == expected_x
        assert y_coordinate == expected_y


def test_create_measurement_groups() -> None:
    root_element = load_sample_xml()

    measurement_groups = create_measurement_groups(root_element)

    assert measurement_groups is not None
    assert len(measurement_groups) == 1

    group = measurement_groups[0]
    assert group.experimental_data_identifier == "Test_Sample"
    assert group.measurement_time == "01-Jan-2023 12:00:00"
    assert group.compensation_matrix_groups is not None
    assert len(group.compensation_matrix_groups) == 1

    assert group.measurements is not None
    assert len(group.measurements) == 1

    measurement = group.measurements[0]
    assert measurement.measurement_identifier is not None
    assert measurement.sample_identifier == "123"
    assert measurement.device_type == DEVICE_TYPE
    assert measurement.written_name is None

    assert measurement.populations is not None
    assert len(measurement.populations) == 1

    root_population = measurement.populations[0]
    assert root_population.written_name == "Test_Sample"
    assert root_population.count == 10000

    assert measurement.data_regions is not None
    assert len(measurement.data_regions) == 4


def test_extract_ellipsoid_vertices() -> None:
    root_element = load_sample_xml()

    ellipsoid_population = None

    lymphocytes = root_element.recursive_find_or_none(
        ["SampleList", "Sample", "SampleNode", "Subpopulations", "Population"]
    )
    assert lymphocytes is not None

    subpops = lymphocytes.find_or_none("Subpopulations")
    assert subpops is not None

    for pop in subpops.findall("Population"):
        if pop.get_attr_or_none("name") == "Ellipsoid Population":
            ellipsoid_population = pop
            break

    assert ellipsoid_population is not None
    assert ellipsoid_population.get_attr_or_none("name") == "Ellipsoid Population"

    gate = ellipsoid_population.find_or_none("Gate")
    assert gate is not None

    gate_type = _get_gate_type(gate)
    assert gate_type == RegionType.ELLIPSOID.value

    ellipsoid_gate = gate.find_or_none(f"gating:{RegionType.ELLIPSOID.value}Gate")
    assert ellipsoid_gate is not None

    x_dim, y_dim = _extract_dimension_identifiers(ellipsoid_gate)
    assert x_dim == "Comp-PE-A"
    assert y_dim == "Comp-BV786-A"

    vertices = _extract_vertices(ellipsoid_gate, gate_type, x_dim, y_dim)

    # Verify vertices
    assert vertices is not None
    assert len(vertices) == 6

    foci_vertices = [v for v in vertices if v.vertex_role == VertexRole.FOCI.value]
    edge_vertices = [v for v in vertices if v.vertex_role == VertexRole.EDGE.value]

    assert len(foci_vertices) == 2
    assert len(edge_vertices) == 4

    # Check coordinates of foci vertices
    assert foci_vertices[0].x_coordinate == 57.89
    assert foci_vertices[0].y_coordinate == 94.97
    assert foci_vertices[1].x_coordinate == 98.10
    assert foci_vertices[1].y_coordinate == 74.02

    # Check coordinates of all 4 edge vertices
    assert edge_vertices[0].x_coordinate == 54.0
    assert edge_vertices[0].y_coordinate == 97.0
    assert edge_vertices[1].x_coordinate == 102.0
    assert edge_vertices[1].y_coordinate == 72.0
    assert edge_vertices[2].x_coordinate == 36.0
    assert edge_vertices[2].y_coordinate == 22.0
    assert edge_vertices[3].x_coordinate == 22.0
    assert edge_vertices[3].y_coordinate == 92.0

    for vertex in vertices:
        assert vertex.x_unit is not None
        assert vertex.y_unit is not None
