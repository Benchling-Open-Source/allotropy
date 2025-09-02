from __future__ import annotations

from io import StringIO
import re
from typing import cast, ClassVar

import pandas as pd

from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import round_to_nearest_well_count
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.luminex_xponent import constants
from allotropy.parsers.utils.pandas import read_csv
from allotropy.parsers.utils.values import assert_not_none, try_float_or_none


class LuminexXponentReader:
    SUPPORTED_EXTENSIONS = "csv"

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        self.lines = read_to_lines(named_file_contents)

        if LuminexXponentReader._is_single_dataset(self.lines):
            (
                self.results_data,
                self.header_data,
                self.calibration_data,
                self.minimum_assay_bead_count_setting,
            ) = SingleDatasetParser.parse(self.lines)
        else:
            reader = CsvReader(self.lines)
            (
                self.results_data,
                self.header_data,
                self.calibration_data,
                self.minimum_assay_bead_count_setting,
            ) = MultipleDatasetParser.parse(reader)

    @staticmethod
    def _is_single_dataset(lines: list[str]) -> bool:
        first_line = lines[0] or ""
        return (
            "INSTRUMENT TYPE" in first_line
            and "WELL LOCATION" in first_line
            and "SAMPLE ID" in first_line
        )


class SingleDatasetParser:
    """
    Adapter to read single dataset CSV exports (all data in a single block)
    and yield the same data structures expected by xPONENT-based downstream code.
    """

    # Columns that are always present in the single-dataset CSV export and are not analyte columns
    FIXED_INPUT_COLUMNS: ClassVar[list[str]] = [
        "INSTRUMENT TYPE",
        "SERIAL NUMBER",
        "SOFTWARE VERSION",
        "PLATE NAME",
        "PLATE START",
        "WELL LOCATION",
        "SAMPLE ID",
    ]

    @staticmethod
    def parse_header(col: str) -> tuple[str, str] | None:
        """Parse a column header into (analyte_label, metric_token).

        The column names have an ID followed by the metric. The metric itself is
        composed of space-separated words that must all be included in
        constants.SINGLE_DATASET_RESULTS_METRIC_WORDS. We therefore split the
        header on spaces and find the earliest split index such that the suffix
        (metric) is entirely composed of known metric words (case-insensitive),
        assigning the prefix to the analyte label.
        """
        header = str(col).strip()
        parts = [p for p in header.split(" ") if p]
        if len(parts) < 2:
            return None

        # Compare words case-insensitively, without extra cleaning
        cleaned = [p.upper() for p in parts]

        # Find earliest index where the suffix is all known metric words
        split_index: int | None = None
        for i in range(1, len(parts)):
            suffix = cleaned[i:]
            if suffix and all(
                s in constants.SINGLE_DATASET_RESULTS_METRIC_WORDS for s in suffix
            ):
                split_index = i
                break

        if split_index is None:
            return None

        analyte_part = " ".join(parts[:split_index]).strip()
        metric_part = " ".join(parts[split_index:]).strip()
        if not analyte_part or not metric_part:
            return None
        return analyte_part, metric_part

    @staticmethod
    def section_name_from_metric(metric_token: str) -> str:
        """Map raw metric tokens to xPONENT-style section names."""
        token_upper = metric_token.upper().strip()
        if token_upper.endswith("AVERAGE MFI"):
            return "Avg Net MFI"
        # Title-case fallback for all other tokens
        return metric_token.title()

    @staticmethod
    def build_section(
        df: pd.DataFrame,
        analyte_labels: list[str],
        headers_map: dict[tuple[str, str], str],
        metric_token: str,
    ) -> pd.DataFrame | None:
        """Build a results section dataframe for the given metric.

        Returns None if no analyte column exists for this metric in the input.
        """

        if metric_token.upper().strip() == "UNITS":
            return SingleDatasetParser.build_units_section(
                df, analyte_labels, headers_map
            )

        at_least_one_present = False
        out = pd.DataFrame()
        out["Location"] = [f"1(1,{w})" for w in df["WELL LOCATION"].astype(str)]
        out["Sample"] = df["SAMPLE ID"].astype(str)
        for analyte in analyte_labels:
            src_col = headers_map.get((analyte, metric_token))
            if src_col:
                at_least_one_present = True
            out[analyte] = df[src_col] if src_col in df.columns else ""

        if not at_least_one_present:
            return None

        if metric_token == "COUNT":  # noqa: S105
            analyte_cols = analyte_labels
            # Convert each analyte column to numeric, coercing errors to NaN then filling with 0.0
            converted = cast(
                pd.DataFrame,
                out[analyte_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0),
            )
            out["Total Events"] = converted.sum(axis=1)
        else:
            out["Total Events"] = ""
        return out.set_index("Location")

    @staticmethod
    def build_units_section(
        df: pd.DataFrame,
        analyte_labels: list[str],
        headers_map: dict[tuple[str, str], str],
    ) -> pd.DataFrame:
        """Build a units section dataframe for the given analyte labels."""
        units_list = []
        at_least_one_present = False
        for analyte in analyte_labels:
            src_col = headers_map.get((analyte, "UNITS"))
            units_list.append(df[src_col][0] if src_col in df.columns else "")
            if src_col:
                at_least_one_present = True

        if not at_least_one_present:
            return pd.DataFrame()

        columns = ["Analyte:", *analyte_labels]
        units: pd.DataFrame = pd.DataFrame(
            [
                columns,
                ["BeadID:", *units_list],
                ["Units:", *[""] * len(analyte_labels)],
            ],
            index=["Analyte:", "BeadID:", "Units:"],
            columns=columns,
        )

        return units

    @staticmethod
    def add_mandatory_columns(
        results: dict[str, pd.DataFrame],
        base_df: pd.DataFrame,
        analyte_labels: list[str],
    ) -> None:
        """Ensure required sections exist (Units, Dilution Factor)."""
        if "Dilution Factor" not in results:
            results["Dilution Factor"] = pd.DataFrame()
            results["Dilution Factor"]["Location"] = [
                f"1(1,{w})" for w in base_df["WELL LOCATION"].astype(str)
            ]
            results["Dilution Factor"]["Sample"] = base_df["SAMPLE ID"].astype(str)
            results["Dilution Factor"]["Dilution Factor"] = ""
            results["Dilution Factor"] = results["Dilution Factor"].set_index(
                "Location"
            )
        if "Units" not in results:
            units_df = pd.DataFrame(
                [
                    ["Analyte:", *analyte_labels],
                    ["BeadID:"],
                    ["Units:"],
                ],
                index=["Analyte:", "BeadID:", "Units:"],
                columns=["Analyte:", *analyte_labels],
            )
            results["Units"] = units_df

    @staticmethod
    def _get_well_count(df: pd.DataFrame) -> int:
        # Count unique values in WELL LOCATION matching Excel-like cell ids: Letter(s) + Number(s)
        # Example matches: A1, B12, AA3
        pattern = r"^[A-Za-z]+\d+$"
        values = df["WELL LOCATION"].astype(str).str.strip()
        matching = values[values.str.match(pattern)]
        unique_count = int(matching.str.upper().nunique())
        nearest = round_to_nearest_well_count(
            unique_count, constants.POSSIBLE_WELL_COUNTS_LUMINEX
        )
        return int(nearest or 0)

    @classmethod
    def parse(
        cls, lines: list[str]
    ) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame, float | None]:
        """Parse single-dataset CSV and return header, calibration, min beads and results tables."""
        df = read_csv(StringIO("\n".join(lines)), header=0)

        analyte_labels: list[str] = []
        seen_labels: set[str] = set()
        headers_map: dict[tuple[str, str], str] = {}
        metric_tokens_ordered: list[str] = []
        seen_metric_tokens: set[str] = set()
        for col in df.columns:
            if col in cls.FIXED_INPUT_COLUMNS:
                continue
            parsed = cls.parse_header(str(col))
            if not parsed:
                continue
            analyte_label, metric = parsed
            headers_map[(analyte_label, metric)] = str(col)
            if (
                metric.upper().strip().endswith("COUNT")
                and analyte_label not in seen_labels
            ):
                analyte_labels.append(analyte_label)
                seen_labels.add(analyte_label)
            if metric not in seen_metric_tokens:
                metric_tokens_ordered.append(metric)
                seen_metric_tokens.add(metric)

        results: dict[str, pd.DataFrame] = {}

        for token in metric_tokens_ordered:
            section_name = cls.section_name_from_metric(token)
            section_df = cls.build_section(df, analyte_labels, headers_map, token)
            if section_df is not None:
                results[section_name] = section_df

        cls.add_mandatory_columns(results, df, analyte_labels)

        # Safely extract optional fields from the input DataFrame without mypy complaints
        _serial_series = (
            df["SERIAL NUMBER"] if "SERIAL NUMBER" in df.columns else pd.Series([""])
        )
        _serial_value = str(_serial_series.iloc[0]) if len(_serial_series) > 0 else ""
        _plate_series = (
            df["PLATE START"] if "PLATE START" in df.columns else pd.Series([""])
        )
        _plate_value = str(_plate_series.iloc[0]) if len(_plate_series) > 0 else ""

        header = (
            pd.DataFrame(
                {
                    0: [
                        "Program",
                        "Build",
                        "Date",
                        "SN",
                        "ProtocolPlate",
                        "ComputerName",
                        "BatchStartTime",
                    ],
                    1: [
                        "xPONENT",
                        "Unknown",
                        "",
                        _serial_value,
                        "Name",
                        "",
                        _plate_value,
                    ],
                    2: ["", "", "", "", "", "", ""],
                    3: ["", "", "", "", "", "", ""],
                    4: ["", "", "", "", cls._get_well_count(df), "", ""],
                    5: ["", "", "", "", "", "", ""],
                }
            )
            .set_index(0)
            .T
        )

        calibration = pd.DataFrame()
        min_beads: float | None = None

        return results, header, calibration, min_beads


class MultipleDatasetParser:
    @classmethod
    def parse(
        cls, reader: CsvReader
    ) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame, float | None]:

        header_data = cls._get_header_data(reader)
        calibration_data = cls._get_calibration_data(reader)
        minimum_assay_bead_count_setting = cls._get_minimum_assay_bead_count_setting(
            reader
        )
        results_data = cls._get_results(reader)
        return (
            results_data,
            header_data,
            calibration_data,
            minimum_assay_bead_count_setting,
        )

    @classmethod
    def _get_header_data(cls, reader: CsvReader) -> pd.DataFrame:
        header_lines = list(reader.pop_until(constants.CALIBRATION_BLOCK_HEADER))
        # Header has a weird structure where there rows have varying number of columns, so we need
        # special handling before passing to read_csv.
        n_columns = max(len(line.split(",")) for line in header_lines)
        if n_columns < constants.EXPECTED_HEADER_COLUMNS:
            msg = "Unable to parse header. Not enough data."
            raise AllotropeConversionError(msg)

        return (
            read_csv(
                StringIO("\n".join(header_lines)),
                header=None,
                index_col=0,
                names=range(n_columns),
            )
            .dropna(how="all")
            .T
        )

    @classmethod
    def _get_calibration_data(cls, reader: CsvReader) -> pd.DataFrame:
        reader.drop_until_inclusive(constants.CALIBRATION_BLOCK_HEADER)
        return assert_not_none(
            reader.pop_csv_block_as_df(constants.LUMINEX_EMPTY_PATTERN)
        )

    @classmethod
    def _get_minimum_assay_bead_count_setting(cls, reader: CsvReader) -> float | None:
        reader.drop_until(match_pat='^"?Samples"?,')
        samples_info = assert_not_none(reader.pop(), msg="Unable to find Samples info.")
        try:
            fields = samples_info.replace('"', "").split(",")
            min_bead_count_setting = fields[3].strip()
            # If the min bead count is left empty, the default value is 100, according to software manual.
            if not min_bead_count_setting:
                return 100
        except IndexError as e:
            msg = f"Unable to find minimum bead count setting in Samples info: {samples_info}."
            raise AllotropeConversionError(msg) from e

        return try_float_or_none(min_bead_count_setting)

    @staticmethod
    def _get_results(reader: CsvReader) -> dict[str, pd.DataFrame]:
        reader.drop_until_inclusive("Results")
        reader.drop_empty(constants.LUMINEX_EMPTY_PATTERN)
        results: dict[str, pd.DataFrame] = {}
        while reader.current_line_exists() and "-- CRC --" not in (reader.get() or ""):
            result_title_line = assert_not_none(reader.pop())
            match: re.Match[str] | None
            if not (
                match := re.match(constants.TABLE_HEADER_PATTERN, result_title_line)
            ):
                msg = f"Invalid header block start line: {result_title_line}"
                raise AllotropeParsingError(msg)
            result_title = match.groups()[0]
            table_data = assert_not_none(
                reader.pop_csv_block_as_df(
                    empty_pat=constants.LUMINEX_EMPTY_PATTERN,
                    header=0,
                    index_col=0,
                    na_values=["NaN", "nan", "-NaN", "-nan", "None", "null", "NULL"],
                    keep_default_na=False,  # Prevent pandas from interpreting empty strings as NaN.
                )
            )
            # drop empty columns at the end of the table
            table_data = table_data.loc[:, ~table_data.columns.str.contains("^Unnamed")]
            results[result_title] = table_data
            reader.drop_empty(constants.LUMINEX_EMPTY_PATTERN)

        return results
