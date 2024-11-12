from io import StringIO
import re

import numpy as np

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import LinesReader, SectionLinesReader
from allotropy.parsers.utils.pandas import df_to_series_data, read_csv, SeriesData
from allotropy.parsers.utils.values import assert_not_none


class AppBioQuantStudioReader:
    SUPPORTED_EXTENSIONS = "txt"
    header: SeriesData
    sections: dict[str, list[str]]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = SectionLinesReader.create(named_file_contents)

        self.header = self._parse_header(reader)
        self.sections = {}
        for section_reader in reader.iter_sections(r"^\[.+\]"):
            match = re.match(
                r"^\[(.+)\]",
                assert_not_none(section_reader.pop(), "Unexpected empty section"),
            )
            title = str(
                assert_not_none(
                    match, f"Cannot read title section: {section_reader.get()}"
                ).groups()[0]
            )
            self.sections[title] = list(section_reader.lines)[1:]

    def _parse_header(self, reader: LinesReader) -> SeriesData:
        lines = [line.strip() for line in reader.pop_until(r"^\[.+\]") if line.strip()]
        if not lines:
            msg = "Cannot parse data from empty header."
            raise AllotropeConversionError(msg)

        csv_stream = StringIO("\n".join(lines))
        raw_data = read_csv(
            csv_stream, header=None, sep="=", skipinitialspace=True, index_col=0
        )
        raw_data.index = raw_data.index.str.replace("*", "")
        return df_to_series_data(raw_data.T.replace(np.nan, None))
