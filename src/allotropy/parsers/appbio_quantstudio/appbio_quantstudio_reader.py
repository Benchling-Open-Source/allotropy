from __future__ import annotations

from io import StringIO
import re

import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import LinesReader, SectionLinesReader
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    parse_header_row,
    read_csv,
    read_multisheet_excel,
    SeriesData,
    split_dataframe,
    split_header_and_data,
)
from allotropy.parsers.utils.values import assert_not_none, try_int_or_none


class AppBioQuantStudioReader:
    SUPPORTED_EXTENSIONS = "txt,xlsx"
    header: SeriesData
    sections: dict[str, pd.DataFrame]

    @staticmethod
    def create(named_file_contents: NamedFileContents) -> AppBioQuantStudioReader:
        if named_file_contents.extension == "xlsx":
            raw_contents = read_multisheet_excel(
                named_file_contents.contents,
                header=None,
                engine="calamine",
            )
            contents = {
                name: df.replace(np.nan, None) for name, df in raw_contents.items()
            }
            return AppBioQuantStudioXLSXReader(contents)
        else:
            return AppBioQuantStudioTXTReader(named_file_contents)


class AppBioQuantStudioXLSXReader(AppBioQuantStudioReader):
    def __init__(
        self,
        contents: dict[str, pd.DataFrame],
        header: SeriesData | None = None,
        sections: dict[str, pd.DataFrame] | None = None,
    ) -> None:
        self.contents = contents
        self.header = header or self.get_header(contents)
        self.sections = sections or self.get_sections(contents)

    def get_header(self, contents: dict[str, pd.DataFrame]) -> SeriesData:
        sheet = next(iter(contents.values()))
        df, _ = split_header_and_data(sheet, lambda row: row[0] is None)
        return df_to_series_data(parse_header_row(df.T))

    def get_sections(
        self, contents: dict[str, pd.DataFrame]
    ) -> dict[str, pd.DataFrame]:
        sections = {}
        for name, sheet in contents.items():
            _, data = split_header_and_data(sheet, lambda row: row[0] is None)
            if name == "Results":
                data = data.reset_index(drop=True)
                data, metadata = split_dataframe(
                    data,
                    lambda row: row[0] != "Well" and try_int_or_none(row[0]) is None,
                )
                if metadata is not None:
                    sections["Results Metadata"] = parse_header_row(metadata.T)

            sections[name] = parse_header_row(data.replace(np.nan, None))
        return sections


class AppBioQuantStudioTXTReader(AppBioQuantStudioReader):
    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = SectionLinesReader.create(named_file_contents)
        self.header = self.get_header(reader)
        self.sections = self.get_sections(reader)

    def get_header(self, reader: LinesReader) -> SeriesData:
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

    def get_sections(self, reader: SectionLinesReader) -> dict[str, pd.DataFrame]:
        sections = {}
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
            data_lines = list(section_reader.pop_until_empty())
            section_reader.drop_empty()
            metadata_lines = list(section_reader.pop_until_empty())
            if title == "Results" and metadata_lines:
                # Treat results metadata as an additional section
                csv_stream = StringIO("\n".join(metadata_lines))
                sections["Results Metadata"] = read_csv(
                    csv_stream, header=None, sep="=", skipinitialspace=True, index_col=0
                ).T

            sections[title] = read_csv(
                StringIO("\n".join(data_lines)), sep="\t", thousands=r","
            ).replace(np.nan, None)
        return sections
