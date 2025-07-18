from io import StringIO

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
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
