from enum import Enum
from pathlib import Path

from allotropy.allotrope.models.shared.definitions.custom import TQuantityValueRelativeFluorescenceUnit, \
    TQuantityValueSecondTime
from allotropy.allotrope.schema_mappers.adm.flow_cytometry.benchling._2025._03.flow_cytometry import (
    CompensationMatrix,
    CompensationMatrixGroup,
    DataRegion,
    Measurement,
    MeasurementGroup,
    Metadata,
    Population,
    Vertex,
)
from allotropy.exceptions import AllotropeParsingError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.flowjo import constants
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none, quantity_or_none_from_unit


class RegionType(Enum):
    RECTANGLE = "Rectangle"
    POLYGON = "Polygon"
    ELLIPSOID = "Ellipsoid"
    CURLY_QUAD = "CurlyQuad"


def create_metadata(root_element: StrictXmlElement, file_path: str) -> Metadata:
    cytometer = root_element.recursive_find_or_none(["Cytometers", "Cytometer"])
    keywords = root_element.recursive_find_or_none(["SampleList", "Sample", "Keywords"])

    equipment_serial_number = None
    if keywords is not None:
        keyword_elements = keywords.findall("Keyword")
        for kw in keyword_elements:
            name = kw.get_attr_or_none("name")
            if name in ["CTNUM", "$CYTSN"]:
                equipment_serial_number = kw.get_attr_or_none("value")
                break

    return Metadata(
        file_name=_get_file_path(root_element.get_attr_or_none("nonAutoSaveFileName"))
        or Path(file_path).name,
        unc_path=file_path,
        device_identifier=constants.DEVICE_IDENTIFIER,
        model_number=cytometer.get_attr_or_none("cyt")
        if cytometer is not None
        else None,
        equipment_serial_number=equipment_serial_number,
        data_system_instance_identifier=NOT_APPLICABLE,
        software_name=constants.SOFTWARE_NAME,
        software_version=root_element.get_attr_or_none("flowJoVersion"),
        asm_file_identifier=Path(file_path).with_suffix(".json").name,
    )


def _get_file_path(file_path: str | None) -> str | None:
    if file_path is None:
        return None
    return file_path.split("/")[-1]


def _get_keyword_value_by_name_from_sample(
    sample: StrictXmlElement, name: str
) -> str | None:
    keywords = sample.find_or_none("Keywords")
    if keywords is None:
        return None

    keyword_elements = keywords.findall("Keyword")
    for kw in keyword_elements:
        if kw.get_attr_or_none("name") == name:
            return kw.get_attr_or_none("value")
    return None


def _create_compensation_matrix_groups(
    sample: StrictXmlElement,
) -> list[CompensationMatrixGroup] | None:
    transform_matrix_element = sample.find_or_none("transforms:spilloverMatrix")
    if transform_matrix_element is None:
        return None

    transform_spillovers = transform_matrix_element.findall("transforms:spillover")
    if not transform_spillovers:
        return None

    result = []
    for transform_spillover in transform_spillovers:
        dimension_identifier = transform_spillover.get_namespaced_attr_or_none(
            "data-type", "parameter"
        )

        compensation_matrices = []
        matrix_rows = transform_spillover.findall("transforms:coefficient")
        for matrix_row in matrix_rows:
            matrix_dim_id = matrix_row.get_namespaced_attr_or_none(
                "data-type", "parameter"
            )
            value_str = matrix_row.get_namespaced_attr_or_none("transforms", "value")
            compensation_matrices.append(
                CompensationMatrix(
                    dimension_identifier=matrix_dim_id,
                    compensation_value=try_float_or_none(value_str),
                )
            )

        result.append(
            CompensationMatrixGroup(
                dimension_identifier=dimension_identifier,
                compensation_matrices=compensation_matrices,
            )
        )

    return result


def _create_populations(
    node: StrictXmlElement, parent_id: str | None = None
) -> list[Population]:
    populations = []

    for population in node.findall("Population"):
        written_name = population.get_attr_or_none("name")
        count = population.get_attr_or_none("count")
        current_id = random_uuid_str()
        gate = population.find_or_none("Gate")
        group_identifier = population.get_attr_or_none("owningGroup")
        data_region_identifier = None
        if gate is not None:
            data_region_identifier = gate.get_namespaced_attr_or_none("gating", "id")

        subpops_element = population.find_or_none("Subpopulations")
        if subpops_element is not None:
            # Recursively get subpopulations
            sub_populations = _create_populations(subpops_element, current_id)
        else:
            sub_populations = []

        pop = Population(
            population_identifier=current_id,
            parent_population_identifier=parent_id,
            written_name=written_name,
            data_region_identifier=data_region_identifier,
            count=int(count) if count else None,
            sub_populations=sub_populations,
            custom_info={"group_identifier": group_identifier},
            statistics=None,  # TODO add support for statistics documents
        )
        populations.append(pop)

    return populations


def _process_sample(sample: StrictXmlElement) -> list[Population]:
    sample_node = sample.find_or_none("SampleNode")
    if sample_node is None:
        return []

    subpops_element = sample_node.find_or_none("Subpopulations")
    root_id = random_uuid_str()
    sub_populations = []
    if subpops_element is not None:
        sub_populations = _create_populations(subpops_element, root_id)

    count_str = sample_node.get_attr_or_none("count")
    root_population = Population(
        population_identifier=root_id,
        parent_population_identifier=None,
        written_name=sample_node.get_attr_or_none("name"),
        data_region_identifier=None,
        count=int(count_str) if count_str else None,
        sub_populations=sub_populations,
        statistics=None,
    )

    return [root_population]


def _extract_dimension_identifiers(
    gate_element: StrictXmlElement,
) -> tuple[str | None, str | None]:
    """
    Extract dimension identifiers from a gate element.

    Args:
        gate_element: The gate element to extract dimensions from

    Returns:
        tuple[str | None, str | None]: A tuple containing the x and y dimension identifiers
    """
    x_dim = None
    y_dim = None

    dimensions = gate_element.findall("gating:dimension")

    # Extract x dimension (first dimension)
    if len(dimensions) > 0:
        x_dimension = dimensions[0]
        fcs_dimension = x_dimension.find_or_none("data-type:fcs-dimension")
        if fcs_dimension is not None:
            x_dim = fcs_dimension.get_namespaced_attr_or_none("data-type", "name")

    # Extract y dimension (second dimension)
    if len(dimensions) > 1:
        y_dimension = dimensions[1]
        fcs_dimension = y_dimension.find_or_none("data-type:fcs-dimension")
        if fcs_dimension is not None:
            y_dim = fcs_dimension.get_namespaced_attr_or_none("data-type", "name")

    return x_dim, y_dim


def _get_gate_type(gate_element: StrictXmlElement) -> str | None:
    for region_type in RegionType:
        if gate_element.find_or_none(f"gating:{region_type.value}Gate") is not None:
            return region_type.value
    return None


def _extract_vertices(
    gate_element: StrictXmlElement, gate_type: str | None, x_dim: str | None = None, y_dim: str | None = None
) -> list[Vertex] | None:
    """
    Extract vertex coordinates from a gate element.

    Handles different gate types:
    - Polygon: Extract vertices from gating:vertex elements
    - Rectangle: Extract min/max coordinates to create 4 vertices
    - CurlyQuad: Extract min/max coordinates to create a vertex
    - Ellipsoid: Not supported yet (TODO)

    Returns:
        list[Vertex] | None: List of vertices if found, None otherwise
    """
    vertices = []

    # Determine units based on dimension identifiers
    x_unit = TQuantityValueSecondTime.unit if x_dim is not None and x_dim.lower() == "time" else TQuantityValueRelativeFluorescenceUnit.unit
    y_unit = TQuantityValueSecondTime.unit if y_dim is not None and y_dim.lower() == "time" else TQuantityValueRelativeFluorescenceUnit.unit

    # For Polygon gates, extract vertices from vertex elements
    if gate_type == RegionType.POLYGON.value:
        vertex_elements = gate_element.findall("gating:vertex")

        if not vertex_elements:
            return None

        for vertex in vertex_elements:
            coordinates = vertex.findall("gating:coordinate")
            if len(coordinates) >= 2:
                x_coord = coordinates[0].get_namespaced_attr_or_none(
                    "data-type", "value"
                )
                y_coord = coordinates[1].get_namespaced_attr_or_none(
                    "data-type", "value"
                )
                if x_coord and y_coord:
                    vertices.append(
                        Vertex(
                            x_coordinate=quantity_or_none_from_unit(x_unit, float(x_coord)),
                            y_coordinate=quantity_or_none_from_unit(y_unit, float(y_coord)),
                        )
                    )

        return vertices if vertices else None

    # For Rectangle and CurlyQuad gates, extract min/max coordinates
    elif gate_type in [RegionType.RECTANGLE.value, RegionType.CURLY_QUAD.value]:
        x_min = None
        x_max = None
        y_min = None
        y_max = None

        dimension_elements = gate_element.findall("gating:dimension")

        if len(dimension_elements) > 0:
            # First dimension (X)
            x_dimension = dimension_elements[0]

            x_min_element = x_dimension.find_or_none("gating:min")
            if x_min_element is not None:
                x_min_value = x_min_element.get_namespaced_attr_or_none(
                    "data-type", "value"
                )
                if x_min_value is not None:
                    x_min = float(x_min_value)
            else:
                x_min_value = x_dimension.get_namespaced_attr_or_none("gating", "min")
                if x_min_value is not None:
                    x_min = float(x_min_value)

            x_max_element = x_dimension.find_or_none("gating:max")
            if x_max_element is not None:
                x_max_value = x_max_element.get_namespaced_attr_or_none(
                    "data-type", "value"
                )
                if x_max_value is not None:
                    x_max = float(x_max_value)
            else:
                x_max_value = x_dimension.get_namespaced_attr_or_none("gating", "max")
                if x_max_value is not None:
                    x_max = float(x_max_value)

        if len(dimension_elements) > 1:
            # Second dimension (Y)
            y_dimension = dimension_elements[1]

            y_min_element = y_dimension.find_or_none("gating:min")
            if y_min_element is not None:
                y_min_value = y_min_element.get_namespaced_attr_or_none(
                    "data-type", "value"
                )
                if y_min_value is not None:
                    y_min = float(y_min_value)
            else:
                y_min_value = y_dimension.get_namespaced_attr_or_none("gating", "min")
                if y_min_value is not None:
                    y_min = float(y_min_value)

            y_max_element = y_dimension.find_or_none("gating:max")
            if y_max_element is not None:
                y_max_value = y_max_element.get_namespaced_attr_or_none(
                    "data-type", "value"
                )
                if y_max_value is not None:
                    y_max = float(y_max_value)
            else:
                y_max_value = y_dimension.get_namespaced_attr_or_none("gating", "max")
                if y_max_value is not None:
                    y_max = float(y_max_value)

        if (
            x_min is not None
            and y_min is not None
            and x_max is not None
            and y_max is not None
        ):
            vertices = [
                Vertex(x_coordinate=quantity_or_none_from_unit(x_unit, x_min), y_coordinate=quantity_or_none_from_unit(y_unit, y_min)),
                Vertex(x_coordinate=quantity_or_none_from_unit(x_unit, x_min), y_coordinate=quantity_or_none_from_unit(y_unit, y_max)),
                Vertex(x_coordinate=quantity_or_none_from_unit(x_unit, x_max), y_coordinate=quantity_or_none_from_unit(y_unit, y_max)),
                Vertex(x_coordinate=quantity_or_none_from_unit(x_unit, x_max), y_coordinate=quantity_or_none_from_unit(y_unit, y_min)),
            ]
        elif x_min is not None and y_min is not None:
            vertices = [Vertex(x_coordinate=quantity_or_none_from_unit(x_unit, x_min), y_coordinate=quantity_or_none_from_unit(y_unit, y_min))]
        elif x_min is not None and y_max is not None:
            vertices = [Vertex(x_coordinate=quantity_or_none_from_unit(x_unit, x_min), y_coordinate=quantity_or_none_from_unit(y_unit, y_max))]
        elif x_max is not None and y_min is not None:
            vertices = [Vertex(x_coordinate=quantity_or_none_from_unit(x_unit, x_max), y_coordinate=quantity_or_none_from_unit(y_unit, y_min))]
        elif x_max is not None and y_max is not None:
            vertices = [Vertex(x_coordinate=quantity_or_none_from_unit(x_unit, x_max), y_coordinate=quantity_or_none_from_unit(y_unit, y_max))]
        else:
            return None

        return vertices if vertices else None

    # TODO: Add support for Ellipsoid gates
    elif gate_type == RegionType.ELLIPSOID.value:
        return None

    return None


def _create_data_regions(sample: StrictXmlElement) -> list[DataRegion]:
    data_regions: list[DataRegion] = []
    sample_node = sample.find_or_none("SampleNode")
    if sample_node is None:
        return data_regions

    def process_population(population: StrictXmlElement) -> None:
        gate = population.find_or_none("Gate")
        if gate is not None:
            gate_type = _get_gate_type(gate)
            if gate_type is None:
                return

            gate_element = gate.find_or_none(f"gating:{gate_type}Gate")
            if gate_element is None:
                return

            x_dim, y_dim = _extract_dimension_identifiers(gate_element)
            vertices = _extract_vertices(gate_element, gate_type, x_dim, y_dim)

            data_regions.append(
                DataRegion(
                    region_data_identifier=gate.get_namespaced_attr_or_none(
                        "gating", "id"
                    ),
                    region_data_type=gate_type,
                    parent_data_region_identifier=gate.get_namespaced_attr_or_none(
                        "gating", "parent_id"
                    ),
                    x_coordinate_dimension_identifier=x_dim,
                    y_coordinate_dimension_identifier=y_dim,
                    vertices=vertices,
                )
            )

        subpops_element = population.find_or_none("Subpopulations")
        if subpops_element is not None:
            for subpop in subpops_element.findall("Population"):
                process_population(subpop)

    subpops_element = sample_node.find_or_none("Subpopulations")
    if subpops_element is not None:
        for population in subpops_element.findall("Population"):
            process_population(population)

    return data_regions


def create_measurement_groups(root_element: StrictXmlElement) -> list[MeasurementGroup]:
    sample_list = root_element.find_or_none("SampleList")
    if sample_list is None:
        msg = "No SampleList element found in XML file."
        raise AllotropeParsingError(msg)

    samples = sample_list.findall("Sample")

    result = []
    for sample in samples:
        sample_node = sample.find("SampleNode")
        experimental_data_identifier = sample_node.get_attr_or_none("name")

        measurement_group = MeasurementGroup(
            experimental_data_identifier=experimental_data_identifier,
            measurement_time=_get_measurement_time(sample),
            analyst=_get_keyword_value_by_name_from_sample(sample, "$OP"),
            compensation_matrix_groups=_create_compensation_matrix_groups(sample),
            measurements=[
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    sample_identifier=sample_node.get_attr("sampleID"),
                    location_identifier=_get_keyword_value_by_name_from_sample(
                        sample, "WELL ID"
                    ),
                    well_plate_identifier=_get_keyword_value_by_name_from_sample(
                        sample, "PLATE ID"
                    ),
                    written_name=_get_keyword_value_by_name_from_sample(sample, "$SRC"),
                    device_type=constants.DEVICE_TYPE,
                    method_version=root_element.get_attr_or_none("version"),
                    data_processing_time=root_element.get_attr_or_none("modDate"),
                    processed_data_identifier=random_uuid_str(),
                    populations=_process_sample(sample),
                    data_regions=_create_data_regions(sample),
                )
            ],
        )
        result.append(measurement_group)

    return result


def _get_measurement_time(sample: StrictXmlElement) -> str | None:
    date = _get_keyword_value_by_name_from_sample(sample, "$DATE")
    etim = _get_keyword_value_by_name_from_sample(sample, "$ETIM")
    if date is None or etim is None:
        return None
    return f"{date} {etim}"
