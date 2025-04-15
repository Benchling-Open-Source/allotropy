from __future__ import annotations

from enum import Enum
import math
from pathlib import Path

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueSecondTime,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.allotrope.schema_mappers.adm.flow_cytometry.benchling._2025._03.flow_cytometry import (
    CompensationMatrix,
    CompensationMatrixGroup,
    DataRegion,
    Measurement,
    MeasurementGroup,
    Metadata,
    Population,
    Statistic,
    StatisticDimension,
    Vertex,
)
from allotropy.exceptions import AllotropeParsingError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.flowjo import constants
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none

# Map of FlowJo field names to statistic datum roles and units
FLOWJO_STATISTIC_MAP = {
    # Fluorescence statistics
    "Median": {"role": TStatisticDatumRole.median_role.value, "unit": "RFU"},
    "CV": {
        "role": TStatisticDatumRole.coefficient_of_variation_role.value,
        "unit": "%",
    },
    "Robust CV": {
        "role": TStatisticDatumRole.robust_coefficient_of_variation_role.value,
        "unit": "%",
    },
    "Mean": {"role": TStatisticDatumRole.arithmetic_mean_role.value, "unit": "RFU"},
    "Geometric Mean": {
        "role": TStatisticDatumRole.geometric_mean_role.value,
        "unit": "RFU",
    },
    "Percentile": {"role": TStatisticDatumRole.percentile_role.value, "unit": "RFU"},
    "SD": {
        "role": TStatisticDatumRole.standard_deviation_role.value,
        "unit": "(unitless)",
    },
    "MADExact": {
        "role": TStatisticDatumRole.median_absolute_deviation_percentile_role.value,
        "unit": "(unitless)",
    },
    "Robust SD": {
        "role": TStatisticDatumRole.robust_standard_deviation_role.value,
        "unit": "(unitless)",
    },
    "Median Abs Dev": {
        "role": TStatisticDatumRole.median_absolute_deviation_role.value,
        "unit": "(unitless)",
    },
    # Count statistics
    "fj.stat.freqofparent": {
        "role": TStatisticDatumRole.frequency_of_parent_role.value,
        "unit": "%",
    },
    "fj.stat.freqofgrandparent": {
        "role": TStatisticDatumRole.frequency_of_grandparent_role.value,
        "unit": "%",
    },
    "fj.stat.freqoftotal": {
        "role": TStatisticDatumRole.frequency_of_total_role.value,
        "unit": "%",
    },
}

# Identify statistics that belong to the "Count" feature
COUNT_FIELDS = [
    "fj.stat.freqofparent",
    "fj.stat.freqofgrandparent",
    "fj.stat.freqoftotal",
    "fj.stat.freqof",
]
FLUORESCENCE_FIELDS = [
    "Median",
    "CV",
    "Robust CV",
    "Mean",
    "Geometric Mean",
    "Percentile",
    "SD",
    "MADExact",
    "Robust SD",
    "Median Abs Dev",
]


class RegionType(Enum):
    RECTANGLE = "Rectangle"
    POLYGON = "Polygon"
    ELLIPSOID = "Ellipsoid"
    CURLY_QUAD = "CurlyQuad"


class VertexRole(Enum):
    FOCI = "foci"
    EDGE = "edge"


class VertexExtractor:
    """Base class for vertex extraction strategies."""

    def __init__(
        self, gate_element: StrictXmlElement, x_dim: str | None, y_dim: str | None
    ):
        self.gate_element = gate_element
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.x_unit = (
            TQuantityValueSecondTime.unit
            if x_dim is not None and x_dim.lower() == "time"
            else TQuantityValueRelativeFluorescenceUnit.unit
        )
        self.y_unit = (
            TQuantityValueSecondTime.unit
            if y_dim is not None and y_dim.lower() == "time"
            else TQuantityValueRelativeFluorescenceUnit.unit
        )

    def extract(self) -> list[Vertex] | None:
        """Extract vertices from the gate element."""
        raise NotImplementedError

    @staticmethod
    def build(
        gate_element: StrictXmlElement,
        gate_type: str | None,
        x_dim: str | None,
        y_dim: str | None,
    ) -> VertexExtractor | None:
        if not gate_type:
            return None

        extractors = {
            RegionType.POLYGON.value: PolygonVertexExtractor,
            RegionType.RECTANGLE.value: RectangleVertexExtractor,
            RegionType.CURLY_QUAD.value: RectangleVertexExtractor,
            RegionType.ELLIPSOID.value: EllipsoidVertexExtractor,
        }

        extractor = extractors.get(gate_type)
        if not extractor:
            msg = f"Gate type '{gate_type}' is not currently supported"
            raise AllotropeParsingError(msg)

        strategy = extractor(gate_element, x_dim, y_dim)
        return strategy


class PolygonVertexExtractor(VertexExtractor):
    """Strategy for extracting vertices from Polygon gates."""

    def extract(self) -> list[Vertex] | None:
        result = []
        vertex_elements = self.gate_element.findall("gating:vertex")

        if not vertex_elements:
            return None

        for vertex in vertex_elements:
            coordinates = vertex.findall("gating:coordinate")
            if len(coordinates) < 2:
                return None

            x = coordinates[0].get_namespaced_attr_or_none("data-type", "value")
            y = coordinates[1].get_namespaced_attr_or_none("data-type", "value")

            if x is not None and y is not None:
                result.append(
                    Vertex(
                        x_coordinate=float(x),
                        y_coordinate=float(y),
                        x_unit=self.x_unit,
                        y_unit=self.y_unit,
                    )
                )

        return result if result else None


class RectangleVertexExtractor(VertexExtractor):
    """Strategy for extracting vertices from Rectangle and CurlyQuad gates."""

    def extract(self) -> list[Vertex] | None:
        result = []
        dimension_elements = self.gate_element.findall("gating:dimension")

        if len(dimension_elements) < 2:
            return None

        def _get_gate_value_from_dimension(
            dimension: StrictXmlElement, gate_type: str
        ) -> str | None:
            element = dimension.find_or_none(f"gating:{gate_type}")
            return (
                element.get_namespaced_attr_or_none("data-type", "value")
                if element
                else dimension.get_namespaced_attr_or_none("gating", gate_type)
            )

        x_min = _get_gate_value_from_dimension(dimension_elements[0], "min")
        x_max = _get_gate_value_from_dimension(dimension_elements[0], "max")
        y_min = _get_gate_value_from_dimension(dimension_elements[1], "min")
        y_max = _get_gate_value_from_dimension(dimension_elements[1], "max")

        for x, y in ((x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min)):
            if x is not None and y is not None:
                result.append(
                    Vertex(
                        x_coordinate=float(x),
                        y_coordinate=float(y),
                        x_unit=self.x_unit,
                        y_unit=self.y_unit,
                    )
                )

        return result if result else None


class EllipsoidVertexExtractor(VertexExtractor):
    """Strategy for extracting vertices from Ellipsoid gates."""

    def extract(self) -> list[Vertex] | None:
        result = []

        def _extract_coordinate_values(
            coords: list[StrictXmlElement],
        ) -> tuple[str | None, str | None]:
            x_value = (
                coords[0].get_namespaced_attr_or_none("data-type", "value")
                if coords
                else None
            )
            y_value = (
                coords[1].get_namespaced_attr_or_none("data-type", "value")
                if len(coords) > 1
                else None
            )
            return x_value, y_value

        def _add_vertex_with_role(vertex_element: StrictXmlElement, role: str) -> None:
            coords = vertex_element.findall("gating:coordinate")
            x_value, y_value = _extract_coordinate_values(coords)

            if x_value is not None and y_value is not None:
                result.append(
                    Vertex(
                        x_coordinate=float(x_value),
                        y_coordinate=float(y_value),
                        x_unit=self.x_unit,
                        y_unit=self.y_unit,
                        vertex_role=role,
                    )
                )

        foci_vertices = self.gate_element.findall("gating:foci/gating:vertex")
        for vertex in foci_vertices:
            _add_vertex_with_role(vertex, VertexRole.FOCI.value)

        edge_vertices = self.gate_element.findall("gating:edge/gating:vertex")
        for vertex in edge_vertices:
            _add_vertex_with_role(vertex, VertexRole.EDGE.value)

        return result if result else None


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
        model_number=cytometer.get_attr_or_none("cyt") if cytometer else None,
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


def _extract_statistics(population: StrictXmlElement) -> list[Statistic] | None:
    """
    Extract statistics from a population element.

    Args:
        population: The population element to extract statistics from

    Returns:
        list[Statistic] | None: List of statistics if found, None otherwise
    """
    fluorescence_dimensions = []
    count_dimensions = []

    statistic_elements = population.findall("Statistic")
    if not statistic_elements:
        return None

    for statistic in statistic_elements:
        name = statistic.get_attr_or_none("name")
        dimension_id = statistic.get_attr_or_none("id")
        value_str = statistic.get_attr_or_none("value")

        if not (name and value_str):
            continue

        value = try_float_or_none(value_str)
        if value is None or math.isnan(value):
            continue

        stat_info = FLOWJO_STATISTIC_MAP.get(name)
        if stat_info is None:
            continue

        dimension = StatisticDimension(
            dimension_identifier=dimension_id,
            value=value * 100 if name in COUNT_FIELDS else value,
            unit=stat_info["unit"],
            has_statistic_datum_role=stat_info["role"],
        )

        if name in FLUORESCENCE_FIELDS:
            fluorescence_dimensions.append(dimension)
        elif name in COUNT_FIELDS:
            count_dimensions.append(dimension)

    statistics = []

    if fluorescence_dimensions:
        statistics.append(
            Statistic(
                statistical_feature="fluorescence",
                statistic_dimension=fluorescence_dimensions,
            )
        )

    if count_dimensions:
        statistics.append(
            Statistic(statistical_feature="count", statistic_dimension=count_dimensions)
        )

    return statistics if statistics else None


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

        statistics = None
        subpops_element = population.find_or_none("Subpopulations")
        if subpops_element is not None:
            statistics = _extract_statistics(subpops_element)
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
            statistics=statistics,
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
    # Handle special case for CurlyQuad
    if gate_element.find_or_none("gating:CurlyQuad") is not None:
        return RegionType.CURLY_QUAD.value

    for region_type in RegionType:
        if gate_element.find_or_none(f"gating:{region_type.value}Gate") is not None:
            return region_type.value
    return None


def _extract_vertices(
    gate_element: StrictXmlElement,
    gate_type: str | None,
    x_dim: str | None = None,
    y_dim: str | None = None,
) -> list[Vertex] | None:
    """
    Extract vertex coordinates from a gate element.

    Handles different gate types:
    - Polygon: Extract vertices from gating:vertex elements
    - Rectangle: Extract min/max coordinates to create 4 vertices
    - CurlyQuad: Extract min/max coordinates to create a vertex
    - Ellipsoid: Extract foci (2 vertices) and edge (4 vertices) coordinates

    Returns:
        list[Vertex] | None: List of vertices if found, None otherwise
    """
    extractor = VertexExtractor.build(gate_element, gate_type, x_dim, y_dim)
    if extractor is None:
        return None
    return extractor.extract()


def _create_data_regions(sample: StrictXmlElement) -> list[DataRegion]:
    data_regions: list[DataRegion] = []
    sample_node = sample.find_or_none("SampleNode")

    def _process_population(population: StrictXmlElement) -> None:
        if not (gate := population.find_or_none("Gate")) or not (
            gate_type := _get_gate_type(gate)
        ):
            return
        if gate_type == RegionType.CURLY_QUAD.value:
            gate_element = gate.find_or_none("gating:CurlyQuad")
        else:
            gate_element = gate.find_or_none(f"gating:{gate_type}Gate")

        if not gate_element:
            return

        x_dim, y_dim = _extract_dimension_identifiers(gate_element)
        vertices = _extract_vertices(gate_element, gate_type, x_dim, y_dim)
        data_regions.append(
            DataRegion(
                region_data_identifier=gate.get_namespaced_attr_or_none("gating", "id"),
                region_data_type=gate_type,
                parent_data_region_identifier=gate.get_namespaced_attr_or_none(
                    "gating", "parent_id"
                ),
                x_coordinate_dimension_identifier=x_dim,
                y_coordinate_dimension_identifier=y_dim,
                vertices=vertices,
            )
        )

    def process_population(population: StrictXmlElement | None) -> None:
        if not population:
            return
        _process_population(population)
        if not (subpops_element := population.find_or_none("Subpopulations")):
            return
        for subpop in subpops_element.findall("Population"):
            process_population(subpop)

    process_population(sample_node)

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
