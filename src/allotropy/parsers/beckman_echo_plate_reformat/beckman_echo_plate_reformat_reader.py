from io import StringIO
import re

import numpy as np
import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import (
    InvertedLinesReader,
    LinesReader,
    SectionLinesReader,
)
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    read_csv,
    SeriesData,
)
from allotropy.parsers.utils.values import assert_not_none


class BeckmanEchoPlateReformatReader:
    SUPPORTED_EXTENSIONS = "csv"
    header: SeriesData
    sections: dict[str, pd.DataFrame]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = LinesReader.create(named_file_contents)
        # header_reader = LinesReader.create(named_file_contents)

        lines = [line.strip() for line in reader.pop_until(r"^\[.+\]") if line.strip()]
        if not lines:
            msg = "Cannot parse data from empty header."
            raise AllotropeConversionError(msg)

        sections = {}

        while not reader.is_empty():
            match = re.match(
                r"^\[(.+)\]",
                assert_not_none(reader.pop(), "Unexpected empty section"),
            )
            if match:
                title = str(
                    assert_not_none(
                        match, f"Cannot read title section: {reader.get()}"
                    ).groups()[0]
                )
                data_lines = list(reader.pop_until_empty())
                reader.drop_empty()

                sections[title] = read_csv(
                    StringIO("\n".join(data_lines)), sep=","
                ).replace(np.nan, None)
            else:
                break

        footer_lines = list(reader.pop_until_empty())
        lines.extend(footer_lines)

        csv_stream = StringIO("\n".join(lines))
        raw_data = read_csv(
            csv_stream, header=None, sep=",", skipinitialspace=True, index_col=0
        )
        raw_data.index = raw_data.index.str.replace("*", "")
        header = df_to_series_data(raw_data.T.replace(np.nan, None))

        self.header = header
        self.sections = sections
