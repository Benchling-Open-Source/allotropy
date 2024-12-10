from io import StringIO
import re

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, EMPTY_STR_OR_CSV_LINE
from allotropy.parsers.utils.pandas import df_to_series_data, read_csv, SeriesData
from allotropy.parsers.utils.values import assert_not_none


class CtlImmunospotReader:
    SUPPORTED_EXTENSIONS = "txt"

    header: SeriesData
    plate_identifier: str | None
    plate_data: dict[str, pd.DataFrame]
    histograms: dict[str, tuple[list[float], list[float]]]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        reader = CsvReader.create(named_file_contents)
        self.header = self._read_header(reader)

        software_version = str(
            assert_not_none(
                re.match(
                    r"^ImmunoSpot ([\d\.]+)$", self.header[str, "Software version"]
                ),
                msg="Unable to parse software version",
            ).group(1)
        )

        if software_version.startswith("7.0.30"):
            (
                self.plate_data,
                self.histograms,
                self.plate_identifier,
            ) = self._parse_7_0_30(reader)
        elif software_version.startswith("7.0.38"):
            (
                self.plate_data,
                self.histograms,
                self.plate_identifier,
            ) = self._parse_7_0_38(reader)
        else:
            msg = f"Unsupported software version: {software_version}"
            raise AllotropeConversionError(msg)

    def _parse_7_0_30(
        self, reader: CsvReader
    ) -> tuple[
        dict[str, pd.DataFrame],
        dict[str, tuple[list[float], list[float]]],
        str | None,
    ]:
        reader.drop_until_inclusive("Unprocessed Data$")

        reader.drop_empty()
        plate_code_line = reader.get() or ""
        assert_not_none(
            re.search("Plate Code =", plate_code_line),
            msg="Unable to find ImmunoSpot Plate Code line",
        )

        plate_identifier = (
            match.group(1)
            if (match := re.search(r"Plate Code = ([\w ]+)", plate_code_line))
            else None
        )
        reader.drop_empty()

        plates: dict[str, pd.DataFrame] = {}
        while reader.current_line_exists():
            raw_name = assert_not_none(
                reader.pop(),
                msg="Unable to read name of assay data.",
            )
            name = raw_name.strip()
            if "Plate Code" in name:
                name = "Spot Count"

            # Read in the plate data, detect end by checking for plate letter label.
            columns = assert_not_none(reader.pop(), "Unable to get column header line")
            reader.pop()
            lines = [columns]
            expected_char = "A"
            while line := reader.pop():
                if line.split()[0] != expected_char:
                    break
                lines.append(line)
                expected_char = chr(ord(expected_char) + 1)

            plates[name] = read_csv(
                StringIO("\n".join(lines)),
                sep=r"\s+",
                # Prevent pandas from rounding decimal values, at the cost of some speed.
                float_precision="round_trip",
                index_col=0,
            )
            reader.drop_until_empty()
            reader.drop_empty()

        # TODO: check all plates are the same size
        return plates, {}, plate_identifier

    def _parse_7_0_38(
        self, reader: CsvReader
    ) -> tuple[
        dict[str, pd.DataFrame],
        dict[str, tuple[list[float], list[float]]],
        str | None,
    ]:
        reader.drop_empty()

        plates: dict[str, pd.DataFrame] = {}
        histograms: dict[str, tuple[list[float], list[float]]] = {}
        while reader.current_line_exists():
            raw_name = assert_not_none(
                reader.pop(),
                msg="Unable to read name of assay data.",
            )
            names = [n.strip() for n in raw_name.strip().split("\t\t") if n.strip()]
            if len(names) == 1 and "Histogram" in names[0]:
                # We currently only handle one histogram, which does not have a label. Raise an error is we get
                # a second one, as we will need to investigate the use case.
                if histograms:
                    msg = "Got unexpected second histogram in input file."
                    raise AllotropeConversionError(msg)
                dimensions, histogram_data = self._read_histogram_7_0_38(reader)
                for well_location, data in histogram_data.items():
                    if well_location in histograms:
                        msg = f"Got multiple histogram entries for well location: {well_location}"
                        raise AllotropeConversionError(msg)
                    histograms[well_location] = (dimensions, data)
            else:
                for name, plate in zip(
                    names, self._read_plate_data_7_0_38(reader), strict=True
                ):
                    plates[name] = plate

            reader.drop_until_empty()
            reader.drop_empty()

        # TODO: check all plates are the same size
        return plates, histograms, None

    def _read_histogram_7_0_38(
        self, reader: CsvReader
    ) -> tuple[list[float], dict[str, list[float]]]:
        dimensions_line = assert_not_none(
            reader.pop(), "Unable to read histogram dimensions line"
        )
        dims = [float(dim) for dim in dimensions_line.strip().split("\t")]
        reader.pop()
        reader.pop()
        histograms: dict[str, list[float]] = {}
        while (line := reader.pop()) is not None:
            if line.startswith("\t"):
                break
            values = line.strip().split("\t")
            histograms[values[0]] = [float(dim) for dim in values[1:]]
        return dims, histograms

    def _read_plate_data_7_0_38(self, reader: CsvReader) -> list[pd.DataFrame]:
        # Read in the plate data, detect end by checking for plate letter label.
        reader.pop()
        columns_line = assert_not_none(reader.pop(), "Unable to get column header line")
        columns = [
            line_split.strip()
            for line_split in columns_line.strip().split("\t\t")
            if line_split.strip()
        ]
        reader.pop()
        reader.pop()
        lines: list[list[str]] = [columns]
        expected_char = "A"
        while line := reader.pop():
            if line.split()[0] != expected_char:
                break
            lines.append(
                [
                    line_split.strip()
                    for line_split in line.strip().split("\t\t")
                    if line_split.strip()
                ]
            )
            expected_char = chr(ord(expected_char) + 1)

        plates: list[pd.DataFrame] = []
        for idx in range(len(lines[0])):
            plates.append(
                read_csv(
                    StringIO("\n".join(line_set[idx] for line_set in lines)),
                    sep=r"\s+",
                    # Prevent pandas from rounding decimal values, at the cost of some speed.
                    float_precision="round_trip",
                    index_col=0,
                )
            )

        return plates

    def _read_header(self, reader: CsvReader) -> SeriesData:
        lines = [line.strip() for line in reader.pop_until_empty(EMPTY_STR_OR_CSV_LINE)]

        def fix_line(line: str) -> str:
            # Add missing key for file path line.
            if line.endswith(".txt") or line.endswith(".xls"):
                line = f"File path: {line}"
            if line.startswith("QC review last updated"):
                date_str = line.split("on ")[1].split(" by")[0]
                line = f"Review Date: {date_str}"
            return line.strip()

        lines = [fix_line(line) for raw_line in lines for line in raw_line.split(";")]
        reader.drop_empty(EMPTY_STR_OR_CSV_LINE)
        if ":" in (reader.get() or ""):
            lines.extend(list(reader.pop_until_empty(EMPTY_STR_OR_CSV_LINE)))

        df = read_csv(
            StringIO("\n".join(lines)),
            sep=r"^([^:]+):\s+",
            header=None,
            engine="python",
            index_col=1,
        ).T
        return df_to_series_data(df, index=-1)
