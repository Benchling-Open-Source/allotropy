from collections import defaultdict

from allotropy.allotrope.models.adm.plate_reader.rec._2025._03.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    Data,
    Mapper,
    MeasurementGroup,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.agilent_gen5_reader import AgilentGen5Reader
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import (
    create_metadata,
    get_processor,
)
from allotropy.parsers.agilent_gen5.constants import (
    NO_MEASUREMENTS_ERROR,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.vendor_parser import VendorParser


def merge_measurement_groups(
    all_groups: list[list[MeasurementGroup]],
) -> list[MeasurementGroup]:
    """Merge multiple lists of measurement groups by well position.

    Each list of measurement groups represents results from a different read/filter set.
    This function combines them so that each well has all its measurements in a single group.
    """
    # Group by well position
    groups_by_well: dict[str, list[MeasurementGroup]] = defaultdict(list)
    for group_list in all_groups:
        for group in group_list:
            # Get the well position from the first measurement in the group
            if group.measurements:
                well_pos = group.measurements[0].location_identifier
                groups_by_well[well_pos].append(group)

    # Merge measurements for each well
    merged_groups = []
    for well_pos in groups_by_well.keys():
        groups = groups_by_well[well_pos]
        # Take metadata from the first group
        base_group = groups[0]
        # Collect all measurements from all groups for this well
        all_measurements = []
        for group in groups:
            all_measurements.extend(group.measurements)

        # Create merged group
        merged_group = MeasurementGroup(
            measurement_time=base_group.measurement_time,
            plate_well_count=base_group.plate_well_count,
            measurements=all_measurements,
        )
        merged_groups.append(merged_group)

    return merged_groups


class AgilentGen5Parser(VendorParser[Data, Model]):
    DISPLAY_NAME = "Agilent Gen5"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = AgilentGen5Reader.SUPPORTED_EXTENSIONS
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        reader = AgilentGen5Reader(named_file_contents)
        context = reader.extract_data_context(named_file_contents.original_file_path)

        # Process each ReadData entry separately and collect results
        all_measurement_groups: list[list[MeasurementGroup]] = []
        all_calculated_data: list[CalculatedDocument] = []

        # Track which reads use the combined results section to avoid processing it multiple times
        combined_results_read_indices: list[int] = []

        for read_index, read_data in enumerate(context.read_data, start=1):
            # Create a test sub-context to check if this is kinetic
            test_context = reader.create_read_context(context, read_data, read_index)
            is_kinetic = test_context.has_kinetic_measurements

            if is_kinetic and len(read_data.measurement_labels) > 1:
                # Split kinetic read into separate sub-reads per filter set
                # Each label gets its own Time section processed separately
                # Sort labels consistently to ensure stable output
                sorted_labels = sorted(
                    read_data.measurement_labels, key=lambda x: (len(x), x)
                )
                for label in sorted_labels:
                    sub_context = reader.create_read_context(
                        context, read_data, read_index, specific_label=label
                    )
                    processor = get_processor(sub_context)
                    measurement_groups, calculated_data = processor.process(sub_context)
                    all_measurement_groups.append(measurement_groups)
                    all_calculated_data.extend(calculated_data)
            else:
                # Check if this read uses the combined results section
                uses_combined_results = (
                    not test_context.has_kinetic_measurements
                    and test_context.results_section
                    and reader.get_results_section() == test_context.results_section
                )

                if uses_combined_results:
                    # Track this read for combined processing
                    combined_results_read_indices.append(read_index)
                else:
                    # Process the read independently
                    sub_context = test_context
                    processor = get_processor(sub_context)
                    measurement_groups, calculated_data = processor.process(sub_context)
                    all_measurement_groups.append(measurement_groups)
                    all_calculated_data.extend(calculated_data)

        # Process all reads that use the combined results section together (only once)
        if combined_results_read_indices:
            # Use the first read's context but with all read_data included
            first_read_index = combined_results_read_indices[0]
            first_read_data = context.read_data[first_read_index - 1]
            combined_context = reader.create_read_context(
                context, first_read_data, first_read_index
            )
            processor = get_processor(combined_context)
            measurement_groups, calculated_data = processor.process(combined_context)
            all_measurement_groups.append(measurement_groups)
            all_calculated_data.extend(calculated_data)

        # Merge measurement groups by well position
        merged_groups = merge_measurement_groups(all_measurement_groups)

        if not merged_groups:
            raise AllotropeConversionError(NO_MEASUREMENTS_ERROR)

        return Data(
            metadata=create_metadata(context.header_data),
            measurement_groups=merged_groups,
            calculated_data=all_calculated_data,
        )
