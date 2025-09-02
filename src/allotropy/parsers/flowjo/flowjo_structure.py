from __future__ import annotations

from collections.abc import Callable
import math
from pathlib import Path
import re

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueSecondTime,
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
from allotropy.parsers.flowjo.constants import (
    ALL_STRUCTURED_KEYWORDS,
    COUNT_FIELDS,
    EQUIPMENT_SERIAL_KEYWORDS,
    FLOWJO_STATISTIC_MAP,
    FLUORESCENCE_FIELDS,
    MEASUREMENT_DOCUMENT_KEYWORDS,
    PROCESSED_DATA_KEYWORDS,
    RegionType,
    SAMPLE_DOCUMENT_KEYWORDS,
    VertexRole,
)
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none


def _filter_unread_data(unread_data: dict[str, str | None]) -> dict[str, str | None]:
    return {
        key: value
        for key, value in unread_data.items()
        if not (
            (value == "")
            or (value is None)
            or (isinstance(value, str) and value.strip() == "")
        )
    }


def _process_keywords(
    keywords: StrictXmlElement | None,
) -> tuple[str | None, dict[str, str]]:
    """
    Process keywords to extract equipment serial number and custom info.

    Returns:
        tuple: (equipment_serial_number, keywords_custom_info)
    """
    if keywords is None:
        return None, {}

    equipment_serial_number = None
    keywords_custom_info = {}

    keyword_elements = keywords.findall("Keyword")
    for kw in keyword_elements:
        name = kw.get_attr_or_none("name")
        value = kw.get_attr_or_none("value")

        # Extract equipment serial number for the main metadata fields
        if name in EQUIPMENT_SERIAL_KEYWORDS:
            equipment_serial_number = value.strip() if value else None

        # Filter out null/empty values and exclude structured keywords
        if (
            name is not None
            and value is not None
            and value.strip() != ""
            and name not in ALL_STRUCTURED_KEYWORDS
            and not _is_device_control_field(name)
        ):
            keywords_custom_info[name] = value.strip()

    return equipment_serial_number, keywords_custom_info


def _extract_keywords_by_filter(
    keywords: StrictXmlElement | None, filter_func: Callable[[str, str], bool]
) -> dict[str, str]:
    """
    Extract keywords from a Keywords element using a filter function.

    Args:
        keywords: The Keywords element to process
        filter_func: Function that takes (name, value) and returns True if keyword should be included

    Returns:
        Dictionary of filtered keywords
    """
    if keywords is None:
        return {}

    result = {}
    keyword_elements = keywords.findall("Keyword")

    for kw in keyword_elements:
        name = kw.get_attr_or_none("name")
        value = kw.get_attr_or_none("value")

        # Basic validation
        if name is None or value is None or value.strip() == "":
            continue

        # Apply filter function
        if filter_func(name, value):
            result[name] = value.strip()

    return result


def _extract_device_control_keywords(
    keywords: StrictXmlElement | None,
) -> dict[str, str]:
    """Extract device control keywords (parameter, laser, and CST fields)."""
    return _extract_keywords_by_filter(
        keywords, lambda name, _: _is_device_control_field(name)
    )


def _extract_general_custom_keywords(
    keywords: StrictXmlElement | None,
) -> dict[str, str]:
    """Extract general custom keywords (excluding structured fields)."""
    return _extract_keywords_by_filter(
        keywords,
        lambda name, _: (
            name not in ALL_STRUCTURED_KEYWORDS
            and name not in ["FJ FCS VERSION", "curGroup"]
            and not _is_device_control_field(name)
        ),
    )


def _extract_device_control_keywords_from_map(mapping: dict[str, str]) -> dict[str, str]:
    """Filter device control keywords using a pre-built mapping."""
    return {name: value for name, value in mapping.items() if _is_device_control_field(name)}


def _extract_general_custom_keywords_from_map(mapping: dict[str, str]) -> dict[str, str]:
    """Filter general custom keywords using a pre-built mapping."""
    result: dict[str, str] = {}
    for name, value in mapping.items():
        if (
            name not in ALL_STRUCTURED_KEYWORDS
            and name not in ["FJ FCS VERSION", "curGroup"]
            and not _is_device_control_field(name)
            and value.strip() != ""
        ):
            result[name] = value
    return result


def _is_device_control_field(keyword: str) -> bool:
    """
    Check if a keyword belongs to device control document.

    Patterns include:
    - Parameter fields: $P{digit}[NRBEVGS], P{digit}(DISPLAY|BS|MS)
    - Laser fields: LASER{digit}(NAME|DELAY|ASF)
    - CST fields: specific cytometer setup and tracking fields
    """
    if not keyword:
        return False

    # Pattern for $P{digit}[NRBEVGS] (e.g., $P1N, $P20R, $P11S)
    dollar_p_pattern = r"^\$P\d+[NRBEVGS]$"

    # Pattern for P{digit}(DISPLAY|BS|MS) (e.g., P1DISPLAY, P20BS, P11MS)
    p_pattern = r"^P\d+(DISPLAY|BS|MS)$"

    # Pattern for LASER{digit}(NAME|DELAY|ASF) (e.g., LASER1NAME, LASER2DELAY, LASER3ASF)
    laser_pattern = r"^LASER\d+(NAME|DELAY|ASF)$"

    # CST and other specific device control fields
    cst_fields = {
        "CST SETUP STATUS",
        "CST BEADS LOT ID",
        "CYTOMETER CONFIG NAME",
        "CYTOMETER CONFIG CREATE DATE",
        "CST SETUP DATE",
        "CST BASELINE DATE",
        "CST BEADS EXPIRED",
        "CST PERFORMANCE EXPIRED",
        "CST REGULATORY STATUS",
    }

    return bool(
        re.match(dollar_p_pattern, keyword)
        or re.match(p_pattern, keyword)
        or re.match(laser_pattern, keyword)
        or keyword in cst_fields
    )


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

            vertex_unread = vertex.get_unread()
            coords_unread = {}
            for i, coord in enumerate(coordinates):
                coord_unread = coord.get_unread()
                # Prefix coordinate data with index to avoid conflicts
                for key, value in coord_unread.items():
                    coords_unread[f"coordinate_{i}_{key}"] = value

            # Combine all unread data and filter it
            all_unread = {**vertex_unread, **coords_unread}
            filtered_unread = _filter_unread_data(all_unread)

            if x is not None and y is not None:
                result.append(
                    Vertex(
                        x_coordinate=float(x),
                        y_coordinate=float(y),
                        x_unit=self.x_unit,
                        y_unit=self.y_unit,
                        custom_info=filtered_unread,
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

        # Collect unread data from all dimension elements
        all_dimension_unread = {}

        def _get_gate_value_from_dimension(
            dimension: StrictXmlElement, gate_type: str
        ) -> str | None:
            element = dimension.find_or_none(f"gating:{gate_type}")
            if element:
                element_unread = element.get_unread()
                for key, value in element_unread.items():
                    all_dimension_unread[f"{gate_type}_element_{key}"] = value
                return element.get_namespaced_attr_or_none("data-type", "value")
            else:
                return dimension.get_namespaced_attr_or_none("gating", gate_type)

        x_min = _get_gate_value_from_dimension(dimension_elements[0], "min")
        x_max = _get_gate_value_from_dimension(dimension_elements[0], "max")
        y_min = _get_gate_value_from_dimension(dimension_elements[1], "min")
        y_max = _get_gate_value_from_dimension(dimension_elements[1], "max")

        # Collect unread data from dimension elements themselves
        for i, dimension in enumerate(dimension_elements):
            dimension_unread = dimension.get_unread()
            for key, value in dimension_unread.items():
                all_dimension_unread[f"dimension_{i}_{key}"] = value

        # Filter the collected unread data
        filtered_unread = _filter_unread_data(all_dimension_unread)

        for x, y in ((x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min)):
            if x is not None and y is not None:
                result.append(
                    Vertex(
                        x_coordinate=float(x),
                        y_coordinate=float(y),
                        x_unit=self.x_unit,
                        y_unit=self.y_unit,
                        custom_info=filtered_unread if filtered_unread else None,
                    )
                )

        return result if result else None


class EllipsoidVertexExtractor(VertexExtractor):
    """Strategy for extracting vertices from Ellipsoid gates."""

    def extract(self) -> list[Vertex] | None:
        result = []
        all_unread_data = {}

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
            # Collect unread data from coordinate elements
            for i, coord in enumerate(coords):
                coord_unread = coord.get_unread()
                for key, value in coord_unread.items():
                    all_unread_data[f"coordinate_{i}_{key}"] = value
            return x_value, y_value

        def _add_vertex_with_role(vertex_element: StrictXmlElement, role: str) -> None:
            coords = vertex_element.findall("gating:coordinate")
            x_value, y_value = _extract_coordinate_values(coords)

            # Collect unread data from vertex element
            vertex_unread = vertex_element.get_unread()
            for key, value in vertex_unread.items():
                all_unread_data[f"vertex_{key}"] = value

            if x_value is not None and y_value is not None:
                # Filter unread data for this vertex
                filtered_unread = _filter_unread_data(all_unread_data.copy())

                result.append(
                    Vertex(
                        x_coordinate=float(x_value),
                        y_coordinate=float(y_value),
                        x_unit=self.x_unit,
                        y_unit=self.y_unit,
                        vertex_role=role,
                        custom_info=filtered_unread if filtered_unread else None,
                    )
                )

        foci_vertices = self.gate_element.findall("gating:foci/gating:vertex")
        for vertex in foci_vertices:
            _add_vertex_with_role(vertex, VertexRole.FOCI.value)

        # Collect unread data from foci elements
        foci_elements = self.gate_element.findall("gating:foci")
        for i, foci in enumerate(foci_elements):
            foci_unread = foci.get_unread()
            for key, value in foci_unread.items():
                all_unread_data[f"foci_{i}_{key}"] = value

        edge_vertices = self.gate_element.findall("gating:edge/gating:vertex")
        for vertex in edge_vertices:
            _add_vertex_with_role(vertex, VertexRole.EDGE.value)

        # Collect unread data from edge elements
        edge_elements = self.gate_element.findall("gating:edge")
        for i, edge in enumerate(edge_elements):
            edge_unread = edge.get_unread()
            for key, value in edge_unread.items():
                all_unread_data[f"edge_{i}_{key}"] = value

        return result if result else None


def create_metadata(root_element: StrictXmlElement, file_path: str) -> Metadata:
    cytometer = root_element.recursive_find_or_none(["Cytometers", "Cytometer"])

    keywords = None
    sample_list = root_element.find_or_none("SampleList")
    if sample_list:
        sample = sample_list.find_or_none("Sample")
        if sample:
            keywords = sample.find_or_none("Keywords")

    equipment_serial_number, keywords_custom_info = _process_keywords(keywords)
    all_custom_info = {}

    if keywords_custom_info:
        all_custom_info.update(keywords_custom_info)

    # Collect unread data from root element (skip fields already captured elsewhere)
    root_unread = root_element.get_unread(
        skip={
            "schemaLocation",
            "version",
            "flowJoVersion",
            "drawRowBorders",
            "drawColumnBorders",
            "hideCompNodes",
            "groupPaneHeight",
            "curGroup",
            "nonAutoSaveFileName",
            "modDate",
            "name",
            "clientTimestamp",
            "homepage",
        }
    )
    if root_unread:
        filtered_root_unread = _filter_unread_data(root_unread)
        # Filter out None values before updating
        non_none_root_unread = {
            k: v for k, v in filtered_root_unread.items() if v is not None
        }
        all_custom_info.update(non_none_root_unread)

    # Collect unread data from cytometer element
    if cytometer:
        cytometer_unread = cytometer.get_unread(
            skip={
                "cyt",
                "widthBasis",
                "useTransform",
                "icon",
                "modDate",
                "name",
                "clientTimestamp",
                "homepage",
                "linFromKW",
                "logFromKW",
                "linMax",
                "logMax",
                "useFCS3",
                "useGain",
                "linearRescale",
                "logMin",
                "linMin",
                "extraNegs",
                "logRescale",
            }
        )
        if cytometer_unread:
            filtered_cytometer_unread = _filter_unread_data(cytometer_unread)
            # Filter out None values before updating
            non_none_cytometer_unread = {
                k: v for k, v in filtered_cytometer_unread.items() if v is not None
            }
            all_custom_info.update(non_none_cytometer_unread)

    # Collect unread data from sample list and sample elements
    if sample_list:
        sample_list_unread = sample_list.get_unread()
        if sample_list_unread:
            filtered_sample_list_unread = _filter_unread_data(sample_list_unread)
            # Filter out None values before updating
            non_none_sample_list_unread = {
                k: v for k, v in filtered_sample_list_unread.items() if v is not None
            }
            all_custom_info.update(non_none_sample_list_unread)

        if sample:
            sample_unread = sample.get_unread()
            if sample_unread:
                filtered_sample_unread = _filter_unread_data(sample_unread)
                # Filter out None values before updating
                non_none_sample_unread = {
                    k: v for k, v in filtered_sample_unread.items() if v is not None
                }
                all_custom_info.update(non_none_sample_unread)

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
        custom_info=all_custom_info,
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
    found_value = None

    for kw in keyword_elements:
        kw_name = kw.get_attr_or_none("name")
        kw_value = kw.get_attr_or_none("value")
        if kw_name == name:
            found_value = kw_value.strip() if kw_value else kw_value
        kw.mark_all_as_read()
    keywords.mark_all_as_read()
    return found_value


def _build_keyword_map(sample: StrictXmlElement) -> tuple[dict[str, str], StrictXmlElement | None]:
    """
    Build a name->value map from the sample's Keywords block once.

    Returns the map and the Keywords element (if present).
    """
    keywords = sample.find_or_none("Keywords")
    if keywords is None:
        return {}, None

    mapping: dict[str, str] = {}
    keyword_elements = keywords.findall("Keyword")
    for kw in keyword_elements:
        kw_name = kw.get_attr_or_none("name")
        kw_value = kw.get_attr_or_none("value")
        if kw_name is not None and kw_value is not None and kw_value.strip() != "":
            mapping[kw_name] = kw_value.strip()
        kw.mark_all_as_read()
    keywords.mark_all_as_read()
    return mapping, keywords


def _create_compensation_matrix_groups(
    transform_matrix_element: StrictXmlElement,
) -> list[CompensationMatrixGroup] | None:
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

            # Collect unread data from matrix row
            matrix_row_unread = matrix_row.get_unread()
            filtered_matrix_row_unread = _filter_unread_data(matrix_row_unread)

            compensation_matrices.append(
                CompensationMatrix(
                    dimension_identifier=matrix_dim_id,
                    compensation_value=try_float_or_none(value_str),
                    custom_info=filtered_matrix_row_unread
                    if filtered_matrix_row_unread
                    else None,
                )
            )

        # Collect unread data from spillover element
        spillover_unread = transform_spillover.get_unread()
        filtered_spillover_unread = _filter_unread_data(spillover_unread)

        result.append(
            CompensationMatrixGroup(
                dimension_identifier=dimension_identifier,
                compensation_matrices=compensation_matrices,
                custom_info=filtered_spillover_unread
                if filtered_spillover_unread
                else None,
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
        population.mark_all_as_read()
        return None

    for statistic in statistic_elements:
        name = statistic.get_attr_or_none("name")
        dimension_id = statistic.get_attr_or_none("id")
        value_str = statistic.get_attr_or_none("value")

        statistic_unread = statistic.get_unread(
            skip={
                "owningGroup",
                "sortPriority",
                "expanded",
            }
        )
        filtered_statistic_unread = _filter_unread_data(statistic_unread)

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
            custom_info=filtered_statistic_unread,
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
            gate.get_namespaced_attr_or_none("gating", "parent_id")
            gate_unread = gate.get_unread()

        statistics = None
        subpops_element = population.find_or_none("Subpopulations")
        if subpops_element is not None:
            statistics = _extract_statistics(subpops_element)
            sub_populations = _create_populations(subpops_element, current_id)
        else:
            sub_populations = []

        # Collect unread data from population element
        population_unread = population.get_unread(
            skip={
                "owningGroup",
                "sortPriority",
                "expanded",
                "count",
            }
        )
        filtered_population_unread = _filter_unread_data(population_unread)

        # Combine custom info
        custom_info = {}
        if group_identifier:
            custom_info["group_identifier"] = group_identifier
        if gate is not None and gate_unread:
            filtered_gate_unread = _filter_unread_data(gate_unread)
            if filtered_gate_unread:
                # Add gate unread data with prefix to avoid conflicts
                gate_custom_info = {
                    f"gate_{key}": value
                    for key, value in filtered_gate_unread.items()
                    if value is not None
                }
                custom_info.update(gate_custom_info)
        if filtered_population_unread:
            # Filter out None values before updating
            non_none_population_unread = {
                k: v for k, v in filtered_population_unread.items() if v is not None
            }
            custom_info.update(non_none_population_unread)

        final_custom_info = custom_info if custom_info else None

        pop = Population(
            population_identifier=current_id,
            parent_population_identifier=parent_id,
            written_name=written_name,
            data_region_identifier=data_region_identifier,
            count=int(count) if count else None,
            sub_populations=sub_populations,
            custom_info=final_custom_info,
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
        # Mark subpops_element as fully processed
        subpops_element.mark_all_as_read()

    count_str = sample_node.get_attr_or_none("count")
    sample_node.mark_all_as_read()

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
            fcs_dimension.mark_all_as_read()
        x_dimension.mark_all_as_read()

    # Extract y dimension (second dimension)
    if len(dimensions) > 1:
        y_dimension = dimensions[1]
        fcs_dimension = y_dimension.find_or_none("data-type:fcs-dimension")
        if fcs_dimension is not None:
            y_dim = fcs_dimension.get_namespaced_attr_or_none("data-type", "name")
            fcs_dimension.mark_all_as_read()
        y_dimension.mark_all_as_read()

    return x_dim, y_dim


def _get_gate_type(gate_element: StrictXmlElement) -> str | None:
    # Handle special case for CurlyQuad
    curly_quad = gate_element.find_or_none("gating:CurlyQuad")
    if curly_quad is not None:
        curly_quad.mark_all_as_read()
        return RegionType.CURLY_QUAD.value

    for region_type in RegionType:
        gate_type_element = gate_element.find_or_none(f"gating:{region_type.value}Gate")
        if gate_type_element is not None:
            gate_type_element.mark_all_as_read()
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
    vertices = extractor.extract()
    gate_element.mark_all_as_read()
    return vertices


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

        region_data_identifier = gate.get_namespaced_attr_or_none("gating", "id")
        parent_data_region_identifier = gate.get_namespaced_attr_or_none(
            "gating", "parent_id"
        )

        gate_unread = gate.get_unread()
        gate_element_unread = gate_element.get_unread()

        # Combine and filter unread data
        combined_unread = {}
        if gate_unread:
            filtered_gate_unread = _filter_unread_data(gate_unread)
            if filtered_gate_unread:
                # Add gate unread data with prefix
                gate_custom_info = {
                    f"gate_{key}": value
                    for key, value in filtered_gate_unread.items()
                    if value is not None
                }
                combined_unread.update(gate_custom_info)

        if gate_element_unread:
            filtered_gate_element_unread = _filter_unread_data(gate_element_unread)
            if filtered_gate_element_unread:
                # Add gate element unread data with prefix
                gate_element_custom_info = {
                    f"gate_element_{key}": value
                    for key, value in filtered_gate_element_unread.items()
                    if value is not None
                }
                combined_unread.update(gate_element_custom_info)

        data_regions.append(
            DataRegion(
                region_data_identifier=region_data_identifier,
                region_data_type=gate_type,
                parent_data_region_identifier=parent_data_region_identifier,
                x_coordinate_dimension_identifier=x_dim,
                y_coordinate_dimension_identifier=y_dim,
                vertices=vertices,
                custom_info=combined_unread if combined_unread else None,
            )
        )

        population.mark_all_as_read()

    def process_population(population: StrictXmlElement | None) -> None:
        if not population:
            return
        _process_population(population)
        if not (subpops_element := population.find_or_none("Subpopulations")):
            population.mark_all_as_read()
            return
        for subpop in subpops_element.findall("Population"):
            process_population(subpop)
        subpops_element.mark_all_as_read()
        population.mark_all_as_read()

    process_population(sample_node)

    if sample_node:
        sample_node.mark_all_as_read()

    return data_regions


def create_measurement_groups(root_element: StrictXmlElement) -> list[MeasurementGroup]:

    sample_list = root_element.find_or_none("SampleList")
    if sample_list is None:
        msg = "No SampleList element found in XML file."
        raise AllotropeParsingError(msg)

    # Precompute root-level fields (same for all samples)
    root_element_fields = ["modDate", "name", "clientTimestamp", "homepage"]
    pre_root_measurement_fields: dict[str, str] = {}
    for field in root_element_fields:
        value = root_element.get_attr_or_none(field)
        if value is not None and value.strip() != "":
            pre_root_measurement_fields[field] = value.strip()

    root_data_processing_fields = [
        "linFromKW",
        "logFromKW",
        "linMax",
        "logMax",
        "useFCS3",
        "useGain",
        "linearRescale",
        "logMin",
        "linMin",
        "extraNegs",
        "logRescale",
    ]
    pre_root_processing_fields: dict[str, str] = {}
    for field in root_data_processing_fields:
        value = root_element.get_attr_or_none(field)
        if value is not None and value.strip() != "":
            pre_root_processing_fields[field] = value.strip()

    # Precompute cytometer-based fields (if present) once
    cytometer = root_element.recursive_find_or_none(["Cytometers", "Cytometer"])
    pre_cytometer_measurement_fields: dict[str, str] = {}
    pre_cytometer_processing_fields: dict[str, str] = {}
    if cytometer:
        for field in root_element_fields:
            value = cytometer.get_attr_or_none(field)
            if value is not None and value.strip() != "":
                pre_cytometer_measurement_fields[field] = value.strip()

        for field in root_data_processing_fields:
            value = cytometer.get_attr_or_none(field)
            if value is not None and value.strip() != "":
                pre_cytometer_processing_fields[field] = value.strip()

        cytometer.mark_read(
            {
                "cyt",
                "widthBasis",
                "useTransform",
                "icon",
                "manufacturer",
                "serialnumber",
                "transformType",
            }
        )

    # Precompute sample_list measurement fields (if any)
    pre_sample_list_measurement_fields: dict[str, str] = {}
    for field in root_element_fields:
        value = sample_list.get_attr_or_none(field)
        if value is not None and value.strip() != "":
            pre_sample_list_measurement_fields[field] = value.strip()

    samples = sample_list.findall("Sample")

    # Precompute keyword sets for fast membership tests
    measurement_kw_set = set(MEASUREMENT_DOCUMENT_KEYWORDS)
    sample_kw_set = set(SAMPLE_DOCUMENT_KEYWORDS)
    processed_kw_set = set(PROCESSED_DATA_KEYWORDS)

    result = []
    for sample in samples:
        sample_node = sample.find("SampleNode")
        experimental_data_identifier = sample_node.get_attr_or_none("name")

        # Handle compensation matrix groups and their unread data
        compensation_matrix_groups = None
        all_custom_info = {}

        transform_matrix_element = sample.find_or_none("transforms:spilloverMatrix")
        if transform_matrix_element is not None:
            compensation_matrix_groups = _create_compensation_matrix_groups(
                transform_matrix_element
            )
            skip_keys = {
                "id",
                "spectral",
                "prefix",
                "editable",
                "color",
                "version",
            }
            matrix_unread_data = transform_matrix_element.get_unread(skip=skip_keys)
            if matrix_unread_data:
                filtered_matrix_unread = _filter_unread_data(matrix_unread_data)
                if filtered_matrix_unread:
                    # Filter out None values before updating
                    non_none_matrix_unread = {
                        k: v for k, v in filtered_matrix_unread.items() if v is not None
                    }
                    all_custom_info.update(non_none_matrix_unread)

        # Collect unread data from SampleNode
        sample_node_unread = sample_node.get_unread(
            skip={
                "sampleID",
                "count",
                "owningGroup",
                "sortPriority",
                "expanded",
                "FJ FCS VERSION",
                "curGroup",
            }
        )
        if sample_node_unread:
            filtered_sample_node_unread = _filter_unread_data(sample_node_unread)
            if filtered_sample_node_unread:
                # Filter out None values before updating
                non_none_sample_node_unread = {
                    k: v
                    for k, v in filtered_sample_node_unread.items()
                    if v is not None
                }
                all_custom_info.update(non_none_sample_node_unread)

        # Build keyword map once per sample for faster repeated access
        keyword_map, keywords_element = _build_keyword_map(sample)

        # Helper uses the prebuilt map first, falling back to XML lookup if needed
        def get_keyword_value(name: str) -> str | None:
            value = keyword_map.get(name)
            if value is not None:
                return value
            return _get_keyword_value_by_name_from_sample(sample, name)

        # Extract measurement-level metadata fields
        measurement_custom_info = {}
        if len(keyword_map) <= len(measurement_kw_set):
            for name, value in keyword_map.items():
                if name in measurement_kw_set:
                    measurement_custom_info[name] = value
        else:
            for name in measurement_kw_set:
                if (value := keyword_map.get(name)) is not None:
                    measurement_custom_info[name] = value

        for field, value in pre_root_measurement_fields.items():
            measurement_custom_info.setdefault(field, value)

        for field, value in pre_sample_list_measurement_fields.items():
            measurement_custom_info.setdefault(field, value)

        # Check current sample element for measurement document fields
        for field in root_element_fields:
            sample_value = sample.get_attr_or_none(field)
            if (
                sample_value is not None
                and sample_value.strip() != ""
                and field not in measurement_custom_info
            ):
                measurement_custom_info[field] = sample_value.strip()

        # Extract sample-level metadata fields
        sample_custom_info = {}
        if len(keyword_map) <= len(sample_kw_set):
            for name, value in keyword_map.items():
                if name in sample_kw_set:
                    sample_custom_info[name] = value
        else:
            for name in sample_kw_set:
                if (value := keyword_map.get(name)) is not None:
                    sample_custom_info[name] = value

        # Extract data processing document-level metadata fields
        data_processing_custom_info = {}
        if len(keyword_map) <= len(processed_kw_set):
            for name, value in keyword_map.items():
                if name in processed_kw_set:
                    data_processing_custom_info[name] = value
        else:
            for name in processed_kw_set:
                if (value := keyword_map.get(name)) is not None:
                    data_processing_custom_info[name] = value

        # Also extract root element fields for data processing document
        root_data_processing_fields = [
            "linFromKW",
            "logFromKW",
            "linMax",
            "logMax",
            "useFCS3",
            "useGain",
            "linearRescale",
            "logMin",
            "linMin",
            "extraNegs",
            "logRescale",
        ]

        for field, value in pre_root_processing_fields.items():
            data_processing_custom_info.setdefault(field, value)

        for field, value in pre_cytometer_measurement_fields.items():
            measurement_custom_info.setdefault(field, value)
        for field, value in pre_cytometer_processing_fields.items():
            data_processing_custom_info.setdefault(field, value)

        device_control_custom_info = _extract_device_control_keywords_from_map(keyword_map)

        keywords_custom_info = _extract_general_custom_keywords_from_map(keyword_map)

        if keywords_custom_info:
            all_custom_info.update(keywords_custom_info)

        measurement_group = MeasurementGroup(
            experimental_data_identifier=experimental_data_identifier,
            measurement_time=_get_measurement_time_from_map(keyword_map)
            or _get_measurement_time(sample),
            analyst=get_keyword_value("$OP"),
            compensation_matrix_groups=compensation_matrix_groups,
            custom_info=all_custom_info if all_custom_info else None,
            measurements=[
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    sample_identifier=sample_node.get_attr("sampleID"),
                    location_identifier=get_keyword_value("WELL ID"),
                    well_plate_identifier=get_keyword_value("PLATE ID"),
                    written_name=get_keyword_value("$SRC"),
                    device_type=constants.DEVICE_TYPE,
                    method_version=root_element.get_attr_or_none("version"),
                    data_processing_time=root_element.get_attr_or_none("modDate"),
                    processed_data_identifier=random_uuid_str(),
                    populations=_process_sample(sample),
                    data_regions=_create_data_regions(sample),
                    custom_info=measurement_custom_info
                    if measurement_custom_info
                    else None,
                    sample_custom_info=sample_custom_info
                    if sample_custom_info
                    else None,
                    data_processing_custom_info=data_processing_custom_info
                    if data_processing_custom_info
                    else None,
                    device_control_custom_info=device_control_custom_info
                    if device_control_custom_info
                    else None,
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


def _get_measurement_time_from_map(mapping: dict[str, str]) -> str | None:
    date = mapping.get("$DATE")
    etim = mapping.get("$ETIM")
    if not date or not etim:
        return None
    return f"{date} {etim}"
