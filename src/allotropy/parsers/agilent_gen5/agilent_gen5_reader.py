from io import StringIO

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    ErrorDocument,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_gen5.agilent_gen5_structure import (
    Gen5DataContext,
    get_concentrations,
    get_identifiers,
    get_kinetic_measurements,
    get_temperature,
    HeaderData,
    KineticData,
    ReadData,
)
from allotropy.parsers.agilent_gen5.constants import (
    MULTIPLATE_FILE_ERROR,
    NO_PLATE_DATA_ERROR,
)
from allotropy.parsers.lines_reader import SectionLinesReader
from allotropy.parsers.utils.pandas import df_to_series_data, read_csv, SeriesData
from allotropy.parsers.utils.values import assert_not_none


class AgilentGen5Reader:
    header_data: SeriesData
    sections: dict[str, list[str]]
    SUPPORTED_EXTENSIONS = "txt"

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = SectionLinesReader.create(named_file_contents)

        plate_readers = list(reader.iter_sections("^Software Version"))
        if not plate_readers:
            raise AllotropeConversionError(NO_PLATE_DATA_ERROR)

        if len(plate_readers) > 1:
            raise AllotropeConversionError(MULTIPLATE_FILE_ERROR)

        plate_reader = plate_readers[0]

        # Header data is all data until the "Procedure Details" section, read in as a cvs
        assert_not_none(
            plate_reader.drop_until("^Software Version"), "Software Version"
        )
        lines = [line for line in plate_reader.pop_until("Procedure Details") if line]
        df = read_csv(
            StringIO("\n".join(lines)),
            header=None,
            index_col=0,
            keep_default_na=False,
            sep="\t",
        ).T
        self.header_data = df_to_series_data(df)

        self.sections = {}
        self.time_sections: dict[str, list[str]] = {}

        # Special handling for the "Procedure Details" section, which has an empty line after the title.
        assert_not_none(
            plate_reader.drop_until("^Procedure Details"), "Procedure Details"
        )
        plate_reader.pop()
        plate_reader.drop_empty()
        # add the plate type to the header data to extract the well count if needed
        self.header_data.series["Plate Type"] = plate_reader.get()
        self.sections["Procedure Details"] = list(plate_reader.pop_until_empty())
        plate_reader.drop_empty()

        # Track the last read label for associating with Time sections
        last_read_label: str | None = None

        while plate_reader.current_line_exists():
            lines = list(plate_reader.pop_until_empty())

            # Skip empty sections
            if not lines:
                plate_reader.drop_empty()
                continue

            section_name = lines[0].split("\t")[0].strip(":")

            # Check if this is a "Read X:label" section (single line, starts with "Read ")
            if len(lines) == 1 and section_name.startswith("Read "):
                last_read_label = section_name
                continue

            # If this is a Time section and we have a read label, store it with the read label
            if section_name == "Time" and last_read_label:
                self.time_sections[last_read_label] = lines
                last_read_label = None
            else:
                self.sections[section_name] = lines

            plate_reader.drop_empty()

    def get_required_section(self, section_name: str) -> list[str]:
        """Get a required section, raises error if not found."""
        section = self.sections.get(section_name)
        if section is None:
            msg = f"Required section '{section_name}' not found."
            raise AllotropeConversionError(msg)
        return section

    @property
    def procedure_details(self) -> list[str]:
        return self.get_required_section("Procedure Details")

    @property
    def layout_section(self) -> list[str] | None:
        return self.sections.get("Layout")

    @property
    def wavelength_section(self) -> list[str] | None:
        return self.sections.get("Wavelength")

    @property
    def time_section(self) -> list[str] | None:
        return self.sections.get("Time")

    @property
    def actual_temperature_section(self) -> list[str] | None:
        return self.sections.get("Actual Temperature")

    def _validate_result_sections(self, result_sections: list[list[str]]) -> None:
        """Validates whether all the result sections dimensions are consistent."""
        first_section = result_sections[0]

        for section in result_sections[1:]:
            if not first_section[0] == section[0] and len(first_section) == len(
                section
            ):
                msg = "All result tables should have the same dimensions."
                raise AllotropeConversionError(msg)

    def get_results_section(self) -> list[str] | None:
        """Returns a valid Results Matrix from the reader sections if found.

        Checks for Results in the reader sections, if not found, creates the results matrix with all
        sections that are correctly formatted as a results table (excluding the Layout section). If
        no tables with results are found, returns None
        """
        if "Results" in self.sections:
            return self.sections["Results"]

        def is_results(section: list[str]) -> bool:
            return (
                len(section) > 2
                and section[1].startswith("\t1")
                and section[2].startswith("A\t")
            )

        result_sections = []
        for name, section in self.sections.items():
            if name == "Layout":
                continue
            if is_results(section):
                result_sections.append(section[1:])

        if result_sections:
            self._validate_result_sections(result_sections)
            return [
                "Results",
                result_sections[0][0],
                *[
                    section[i + 1]
                    for i in range(len(result_sections[0]) - 1)
                    for section in result_sections
                ],
            ]

        return None

    def extract_data_context(self, file_path: str) -> Gen5DataContext:
        """Extract the main context with all ReadData entries."""
        # For the main context, we don't populate kinetic_measurements or results_section
        # Those will be populated per-read in create_read_context
        return Gen5DataContext(
            header_data=HeaderData.create(self.header_data, file_path),
            read_data=ReadData.create(self.procedure_details),
            kinetic_data=KineticData.create(self.procedure_details),
            results_section=[],  # Populated per-read
            sample_identifiers=get_identifiers(self.layout_section),
            concentration_values=get_concentrations(self.layout_section),
            actual_temperature=get_temperature(self.actual_temperature_section),
            kinetic_measurements={},  # Populated per-read
            kinetic_elapsed_time=[],  # Populated per-read
            kinetic_errors={},  # Populated per-read
            wavelength_section=self.wavelength_section,
        )

    def create_read_context(
        self,
        base_context: Gen5DataContext,
        read_data: ReadData,
        read_index: int,
        specific_label: str | None = None,
    ) -> Gen5DataContext:
        """Create a context for a specific ReadData entry with its associated data.

        Args:
            base_context: The main context with all data
            read_data: The ReadData to process
            read_index: The read number (1, 2, 3, etc.)
            specific_label: If provided, only process this specific label (for splitting kinetic reads)
        """
        # Determine which labels to process
        labels_to_process = (
            {specific_label} if specific_label else read_data.measurement_labels
        )

        # Check what data sections exist for this read's labels
        # Try Time sections first (kinetic), then Results sections (endpoint)
        results_section: list[str] = []
        kinetic_measurements: dict[str, list[float | None]] = {}
        kinetic_elapsed_time: list[float] = []
        kinetic_errors: dict[str, list[ErrorDocument]] = {}

        has_time_section = False
        has_results_section = False

        # Check if any labels have Time sections (indicating kinetic data)
        for label in labels_to_process:
            time_key = f"Read {read_index}:{label}"
            if time_key in self.time_sections:
                has_time_section = True
                kinetic_result = get_kinetic_measurements(self.time_sections[time_key])
                if kinetic_result:
                    km, ket, ke = kinetic_result
                    # For the first label found, use its kinetic data
                    if not kinetic_measurements:
                        kinetic_measurements = km
                        kinetic_elapsed_time = ket
                        kinetic_errors = ke

            # Check if any labels have Results sections (indicating endpoint data)
            results_key = f"Read {read_index}:{label}"
            if results_key in self.sections:
                has_results_section = True

        # Based on what sections exist, get the appropriate data
        if has_time_section:
            # This is a kinetic read - we already loaded the kinetic data above
            pass
        elif has_results_section:
            # This is an endpoint read - get the results section
            results_section = self._get_results_for_read(read_index, labels_to_process)
        else:
            # Fallback - check the combined results section
            results_section = self.get_results_section() or []

        # If specific_label was provided, create a modified ReadData with only that label
        if specific_label:
            from dataclasses import replace

            read_data = replace(read_data, measurement_labels={specific_label})

        return Gen5DataContext(
            header_data=base_context.header_data,
            read_data=[read_data],  # Single ReadData for this sub-context
            kinetic_data=base_context.kinetic_data if has_time_section else None,
            results_section=results_section,
            sample_identifiers=base_context.sample_identifiers,
            concentration_values=base_context.concentration_values,
            actual_temperature=base_context.actual_temperature,
            kinetic_measurements=kinetic_measurements,
            kinetic_elapsed_time=kinetic_elapsed_time,
            kinetic_errors=kinetic_errors,
            wavelength_section=base_context.wavelength_section,
        )

    def _get_results_for_read(
        self, read_number: int, measurement_labels: set[str]
    ) -> list[str]:
        """Get and combine results sections for a specific read."""
        # Find all sections matching this read number and labels
        result_sections = []
        for label in sorted(measurement_labels, key=lambda x: (len(x), x)):
            section_name = f"Read {read_number}:{label}"
            if section_name in self.sections:
                result_sections.append(self.sections[section_name][1:])  # Skip header

        if not result_sections:
            # Fallback to combined results section if individual sections not found
            return self.get_results_section() or []

        # Combine the sections similar to get_results_section()
        self._validate_result_sections(result_sections)
        return [
            "Results",
            result_sections[0][0],
            *[
                section[i + 1]
                for i in range(len(result_sections[0]) - 1)
                for section in result_sections
            ],
        ]
