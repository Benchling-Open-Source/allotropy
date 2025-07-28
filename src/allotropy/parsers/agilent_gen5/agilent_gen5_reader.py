from io import StringIO

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
    NO_MEASUREMENTS_ERROR,
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

        while plate_reader.current_line_exists():
            lines = list(plate_reader.pop_until_empty())
            self.sections[lines[0].split("\t")[0].strip(":")] = lines
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
        results_section = self.get_results_section()
        if not results_section:
            self.header_data.get_unread()
            raise AllotropeConversionError(NO_MEASUREMENTS_ERROR)

        kinetic_result = get_kinetic_measurements(self.time_section)
        kinetic_measurements, kinetic_elapsed_time, kinetic_errors = kinetic_result or (
            {},
            [],
            {},
        )

        return Gen5DataContext(
            header_data=HeaderData.create(self.header_data, file_path),
            read_data=ReadData.create(self.procedure_details),
            kinetic_data=KineticData.create(self.procedure_details),
            results_section=results_section,
            sample_identifiers=get_identifiers(self.layout_section),
            concentration_values=get_concentrations(self.layout_section),
            actual_temperature=get_temperature(self.actual_temperature_section),
            kinetic_measurements=kinetic_measurements,
            kinetic_elapsed_time=kinetic_elapsed_time,
            kinetic_errors=kinetic_errors,
            wavelength_section=self.wavelength_section,
        )
