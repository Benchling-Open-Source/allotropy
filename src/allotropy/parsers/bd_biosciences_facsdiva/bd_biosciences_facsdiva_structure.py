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
from allotropy.parsers.bd_biosciences_facsdiva import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none, try_int_or_none

# Map of FACSDiva field names to statistic datum roles and units
FACSDIVA_STATISTIC_MAP = {
    # Fluorescence statistics
    "Median": {"role": TStatisticDatumRole.median_role.value, "unit": "RFU"},
    "CV": {
        "role": TStatisticDatumRole.coefficient_of_variation_role.value,
        "unit": "%",
    },
    "Mean": {"role": TStatisticDatumRole.arithmetic_mean_role.value, "unit": "RFU"},
    "Geometric Mean": {
        "role": TStatisticDatumRole.geometric_mean_role.value,
        "unit": "RFU",
    },
    "SD": {
        "role": TStatisticDatumRole.standard_deviation_role.value,
        "unit": "(unitless)",
    },
    "sum of squares": {
        "role": TStatisticDatumRole.sum_of_squares_role.value,
        "unit": "RFU",
    },
}

FLUORESCENCE_FIELDS = [
    "Median",
    "CV",
    "Mean",
    "Geometric Mean",
    "SD",
    "sum of squares",
]

COUNT_FIELDS = [
    "fj.stat.freqofparent",
    "fj.stat.freqofgrandparent",
    "fj.stat.freqoftotal",
]

# These channels are not part of the compensation matrix
EXCLUDED_CHANNELS = [
    "FSC-A",
    "FSC-H",
    "FSC-W",
    "SSC-A",
    "SSC-H",
    "SSC-W",
    "Time",
]

FIELDS_TO_SKIP = {
    "$OP",  # Already captured as analyst
}

# Fields for device control document
DEVICE_CONTROL_FIELDS = {
    "CST SETUP STATUS",
    "CST BEADS LOT ID",
    "CYTOMETER CONFIG NAME",
    "CYTOMETER CONFIG CREATE DATE",
    "CST SETUP DATE",
    "CST BASELINE DATE",
    "CST BEADS EXPIRED",
}

MEASUREMENT_AGGREGATE_FIELDS = {
    "$BTIM",
}


def _filter_unread_data(unread_data: dict[str, str | None]) -> dict[str, str | None]:
    """Filter out empty, null, or whitespace-only values from unread data."""
    return {
        key: value
        for key, value in unread_data.items()
        if not (
            (value == "")
            or (value is None)
            or (isinstance(value, str) and value.strip() == "")
        )
    }


def _separate_custom_fields(
    custom_info: dict[str, str]
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    device_control_info = {}
    measurement_aggregate_info = {}
    other_info = {}

    for key, value in custom_info.items():
        if key in FIELDS_TO_SKIP:
            continue
        elif key in DEVICE_CONTROL_FIELDS:
            device_control_info[key] = value
        elif key in MEASUREMENT_AGGREGATE_FIELDS:
            measurement_aggregate_info[key] = value
        else:
            other_info[key] = value

    return device_control_info, measurement_aggregate_info, other_info


class RegionType(Enum):
    POLYGON = "POLYGON"
    RECTANGLE = "RECTANGLE"
    BINNER = "BINNER"


def create_metadata(root_element: StrictXmlElement, file_path: str) -> Metadata:
    equipment_serial_number = None
    model_number = None
    all_custom_info = {}

    tube = root_element.recursive_find_or_none(["experiment", "specimen", "tube"])
    if tube:
        equipment_serial_number = tube.find_or_none("data_instrument_serial_number")
        model_number = tube.find_or_none("data_instrument_name")
        tube.mark_read("name")

    software_version = root_element.get_attr_or_none("version")

    # Collect unread data from root element
    root_unread = root_element.get_unread(
        skip={
            "version",
            "release_version",
        }
    )
    if root_unread:
        filtered_root_unread = _filter_unread_data(root_unread)
        all_custom_info.update(filtered_root_unread)

    return Metadata(
        file_name=Path(file_path).name,
        unc_path=file_path,
        device_identifier=constants.DEVICE_IDENTIFIER,
        model_number=model_number.get_text_or_none() if model_number else None,
        equipment_serial_number=equipment_serial_number.get_text_or_none()
        if equipment_serial_number
        else None,
        data_system_instance_identifier=NOT_APPLICABLE,
        software_name=constants.SOFTWARE_NAME,
        software_version=software_version,
        asm_file_identifier=Path(file_path).with_suffix(".json").name,
        custom_info=all_custom_info if all_custom_info else None,
    )


def _extract_statistics_from_calculations(
    tube: StrictXmlElement,
    gate_name: str,
) -> list[Statistic] | None:
    """
    Extract statistics from calculation schedules for a specific gate.

    Args:
        tube: The tube element containing statistics
        gate_name: The name of the gate to extract statistics for

    Returns:
        list[Statistic] | None: List of statistics or None if no statistics found
    """
    statistics_element = tube.find_or_none("statistics_calculations")
    if not statistics_element:
        return None

    fluorescence_dimensions = []
    count_dimensions = []

    for calc_schedule in statistics_element.findall("calculation_schedule"):
        gate = calc_schedule.get_attr_or_none("gate")
        if gate != gate_name:
            calc_schedule.get_unread()
            continue

        parameter = calc_schedule.get_attr_or_none("parameter")

        for calculation in calc_schedule.findall("calculation"):
            formula = calculation.get_attr_or_none("formula")
            value_str = calculation.get_attr_or_none("value")

            if not (formula and value_str):
                continue

            value = try_float_or_none(value_str)
            if value is None or math.isnan(value):
                continue
            if formula == "count":
                # Skip count statistics as it is being reported in the population
                continue

            stat_info = FACSDIVA_STATISTIC_MAP.get(formula)
            if stat_info is None:
                continue

            dimension = StatisticDimension(
                dimension_identifier=parameter,
                value=value,
                unit=stat_info["unit"],
                has_statistic_datum_role=stat_info["role"],
            )

            if formula in FLUORESCENCE_FIELDS:
                fluorescence_dimensions.append(dimension)
            elif formula in COUNT_FIELDS:
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


def _create_data_regions(tube: StrictXmlElement) -> list[DataRegion]:
    """
    Create data regions from gates in the tube.

    Args:
        tube: The tube element containing the gates

    Returns:
        list[DataRegion]: List of DataRegion objects
    """
    data_regions = []

    gates_element = tube.find_or_none("gates")
    if not gates_element:
        return []

    fullname_to_region = {}
    region_to_data_region = {}

    # First pass: collect gate information
    for gate in gates_element.findall("gate"):
        # Skip All Events full name (no region)
        gate_type = gate.get_attr_or_none("type")
        fullname = gate.get_attr_or_none("fullname")

        if gate_type == "EventSource_Classifier":
            continue

        region = gate.find_or_none("region")
        if not region:
            continue

        if not fullname:
            continue

        region_name = region.get_attr_or_none("name")
        if region_name:
            fullname_to_region[fullname] = region_name

        region.mark_read(
            {
                "type",
                "xparm",
                "yparm",
            }
        )

    # Second pass: create data regions
    for gate in gates_element.findall("gate"):
        gate_type = gate.get_attr_or_none("type")
        fullname = gate.get_attr_or_none("fullname")

        if gate_type == "EventSource_Classifier":
            continue

        region = gate.find_or_none("region")
        if not region:
            continue

        if not fullname:
            continue

        region_name = region.get_attr_or_none("name")
        region_type_str = region.get_attr_or_none("type")
        x_param = region.get_attr_or_none("xparm")
        y_param = region.get_attr_or_none("yparm")

        region_type = None
        if region_type_str and "_REGION" in region_type_str:
            base_type = region_type_str.replace("_REGION", "")
            region_type = {e.name: e.value for e in RegionType}.get(base_type)

        # Find parent region identifier using fullname hierarchy
        parent_data_region_id = None
        if "\\" in fullname:
            parent_fullname = fullname.rsplit("\\", 1)[0]
            # Skip All Events as parent (no region)
            if parent_fullname != "All Events":
                parent_data_region_id = fullname_to_region.get(parent_fullname)

        # Extract vertices
        vertices = []
        points_element = region.find_or_none("points")
        if points_element:
            for point in points_element.findall("point"):
                x_coord = try_float_or_none(point.get_attr_or_none("x"))
                y_coord = try_float_or_none(point.get_attr_or_none("y"))

                if x_coord is not None and y_coord is not None:
                    x_unit = (
                        TQuantityValueSecondTime.unit
                        if x_param and "Time" in x_param
                        else TQuantityValueRelativeFluorescenceUnit.unit
                    )
                    y_unit = (
                        TQuantityValueSecondTime.unit
                        if y_param and "Time" in y_param
                        else TQuantityValueRelativeFluorescenceUnit.unit
                    )

                    vertices.append(
                        Vertex(
                            x_coordinate=x_coord,
                            y_coordinate=y_coord,
                            x_unit=x_unit,
                            y_unit=y_unit,
                        )
                    )

        data_region = DataRegion(
            region_data_identifier=region_name,
            region_data_type=region_type,
            parent_data_region_identifier=parent_data_region_id,
            x_coordinate_dimension_identifier=x_param,
            y_coordinate_dimension_identifier=y_param,
            vertices=vertices if vertices else None,
        )

        data_regions.append(data_region)
        if region_name:
            region_to_data_region[region_name] = data_region

    return data_regions


def _create_populations(tube: StrictXmlElement) -> list[Population]:
    """
    Create populations from gates in the tube.

    Args:
        tube: The tube element containing the gates

    Returns:
        list[Population]: List containing the root population with nested subpopulations
    """
    gates_element = tube.find_or_none("gates")
    if not gates_element:
        return []

    fullname_to_gate = {}
    gate_to_children: dict[str, list[str]] = {}
    for gate in gates_element.findall("gate"):
        fullname = gate.get_attr_or_none("fullname")
        if not fullname:
            continue

        fullname_to_gate[fullname] = gate

        parent_elem = gate.find_or_none("parent")
        if parent_elem and parent_elem.get_text_or_none():

            # Build parent path using fullname structure
            if "\\" in fullname:
                parent_path = fullname.rsplit("\\", 1)[0]
                if parent_path not in gate_to_children:
                    gate_to_children[parent_path] = []
                gate_to_children[parent_path].append(fullname)

    def _build_population_tree(full_name: str) -> Population | None:
        _gate = fullname_to_gate.get(full_name)
        if not _gate:
            return None

        pop_id = random_uuid_str()

        name_elem = _gate.find_or_none("name")
        name = name_elem.get_text_or_none() if name_elem else None

        count_elem = _gate.find_or_none("num_events")
        count = try_int_or_none(count_elem.get_text_or_none()) if count_elem else None

        region = _gate.find_or_none("region")
        region_id = region.get_attr_or_none("name") if region else None

        if region:
            region.mark_read(
                {
                    "type",
                    "xparm",
                    "yparm",
                }
            )
        _gate.mark_read(
            {
                "type",
            }
        )

        sub_populations = []
        if full_name in gate_to_children:
            for child_fullname in gate_to_children[full_name]:
                child_pop = _build_population_tree(child_fullname)
                if child_pop:
                    updated_child_pop = Population(
                        population_identifier=child_pop.population_identifier,
                        parent_population_identifier=pop_id,
                        written_name=child_pop.written_name,
                        data_region_identifier=child_pop.data_region_identifier,
                        count=child_pop.count,
                        sub_populations=child_pop.sub_populations,
                        statistics=child_pop.statistics,
                        custom_info=child_pop.custom_info,
                    )
                    sub_populations.append(updated_child_pop)

        # Create this population with its children
        return Population(
            population_identifier=pop_id,
            parent_population_identifier=None,
            written_name=name,
            data_region_identifier=region_id,
            count=count,
            sub_populations=sub_populations if sub_populations else None,
            statistics=_extract_statistics_from_calculations(tube, full_name),
            custom_info=None,
        )

    # Find the root population (All Events) and build the tree
    root_gates = []
    for gate in gates_element.findall("gate"):
        gate_type = gate.get_attr_or_none("type")
        if gate_type == "EventSource_Classifier":
            root_gates.append(gate)
        gate.mark_read(
            {
                "fullname",
            }
        )

    if not root_gates:
        return []

    root_fullname = root_gates[0].get_attr_or_none("fullname")
    if not root_fullname:
        return []

    root_population = _build_population_tree(root_fullname)
    return [root_population] if root_population else []


def _create_compensation_matrix_groups(
    tube: StrictXmlElement,
) -> list[CompensationMatrixGroup] | None:
    """
    Create compensation matrix groups from instrument settings.

    Args:
        tube: The tube element containing instrument settings

    Returns:
        list[CompensationMatrixGroup] | None: List of compensation matrix groups or None
    """
    instrument_settings = tube.find_or_none("instrument_settings")
    if not instrument_settings:
        return None
    # Get fluorescent parameters
    parameters = []
    for param in instrument_settings.findall("parameter"):
        name = param.get_attr_or_none("name")
        if name and name not in EXCLUDED_CHANNELS:
            parameters.append(param)
        else:
            param.get_unread()

    if not parameters:
        return None

    result = []
    for param in parameters:
        dimension_id = param.get_attr_or_none("name")
        compensation_element = param.find_or_none("compensation")

        if not (dimension_id and compensation_element):
            continue

        matrices = []
        # For each coefficient, create a compensation matrix entry
        for i, coef_elem in enumerate(
            compensation_element.findall("compensation_coefficient")
        ):
            coef_value = try_float_or_none(coef_elem.get_text_or_none())
            if coef_value is None:
                continue

            # Get the corresponding parameter for this coefficient
            target_param = parameters[i]
            target_dimension_id = target_param.get_attr_or_none("name")

            if not target_dimension_id:
                continue

            matrices.append(
                CompensationMatrix(
                    dimension_identifier=target_dimension_id,
                    compensation_value=coef_value,
                )
            )
        param.mark_read(
            "type",
        )

        result.append(
            CompensationMatrixGroup(
                dimension_identifier=dimension_id,
                compensation_matrices=matrices if matrices else None,
            )
        )
    instrument_settings.mark_read(
        {
            "name",
            "template",
        }
    )

    return result if result else None


def _process_tube(
    tube: StrictXmlElement, specimen_name: str | None, data_processing_time: str | None
) -> tuple[list[Measurement], dict[str, str]]:
    """
    Process a tube element to create measurements.

    Args:
        tube: The tube element to process

    Returns:
        tuple: (measurements, measurement_aggregate_custom_info)
    """
    tube_name = tube.get_attr("name")

    processed_data_id = random_uuid_str()

    # Extract custom info from keywords
    custom_info = {}
    keywords_element = tube.find_or_none("keywords")
    if keywords_element:
        for keyword in keywords_element.findall("keyword"):
            keyword_name = keyword.get_attr_or_none("name")
            keyword.mark_read("type")

            if keyword_name:
                value_element = keyword.find_or_none("value")
                if value_element:
                    keyword_value = value_element.get_text_or_none()
                    if keyword_value:
                        custom_info[keyword_name] = keyword_value

    (
        device_control_info,
        measurement_aggregate_info,
        other_info,
    ) = _separate_custom_fields(custom_info)

    # Create populations and data regions
    populations = _create_populations(tube)
    data_regions = _create_data_regions(tube)
    measurement = Measurement(
        measurement_identifier=random_uuid_str(),
        sample_identifier=tube_name,
        batch_identifier=specimen_name,
        device_type=constants.DEVICE_TYPE,
        data_processing_time=data_processing_time,
        processed_data_identifier=processed_data_id,
        populations=populations,
        data_regions=data_regions,
        device_control_custom_info=device_control_info if device_control_info else None,
        custom_info=other_info if other_info else None,
    )

    return [measurement], measurement_aggregate_info


def create_measurement_groups(root_element: StrictXmlElement) -> list[MeasurementGroup]:
    """
    Create measurement groups from FACSDiva XML.

    Args:
        root_element: The root element of the FACSDiva XML file

    Returns:
        list[MeasurementGroup]: List of measurement groups
    """

    result = []
    experiment = root_element.find_or_none("experiment")
    if not experiment:
        msg = "No experiment found in the XML file."
        raise AllotropeParsingError(msg)

    measurement_time = experiment.recursive_find_or_none(["specimen", "tube", "date"])
    experiment_identifier = experiment.get_attr_or_none("name")
    analyst = experiment.recursive_find_or_none(["owner_name"])
    export_time = experiment.find_or_none("export_time")
    # Process specimens and tubes
    specimens = experiment.findall("specimen")
    for specimen in specimens:
        specimen_name = specimen.get_attr_or_none("name")
        tubes = specimen.findall("tube")
        for tube in tubes:
            experimental_data_identifier = tube.find_or_none("data_filename")
            measurements, measurement_aggregate_custom_info = _process_tube(
                tube,
                specimen_name,
                export_time.get_text_or_none() if export_time else None,
            )

            compensation_matrix_groups = _create_compensation_matrix_groups(tube)
            measurement_group = MeasurementGroup(
                experimental_data_identifier=experimental_data_identifier.get_text_or_none()
                if experimental_data_identifier
                else None,
                measurement_time=measurement_time.get_text_or_none()
                if measurement_time
                else None,
                analyst=analyst.get_text_or_none() if analyst else None,
                compensation_matrix_groups=compensation_matrix_groups,
                measurements=measurements,
                experiment_identifier=experiment_identifier,
                measurement_aggregate_custom_info=measurement_aggregate_custom_info
                if measurement_aggregate_custom_info
                else None,
            )

            result.append(measurement_group)

    return result
