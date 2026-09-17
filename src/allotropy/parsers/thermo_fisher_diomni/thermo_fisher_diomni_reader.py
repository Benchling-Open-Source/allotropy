"""Reader for Thermo Fisher Diomni Excel files.

Supports both Diomni v4.2.0 and v4.3.0 file formats.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    read_excel,
    SeriesData,
)
from allotropy.types import IOType


class ThermoFisherDiomniReader:
    """Reads and parses Thermo Fisher Diomni Excel files."""

    SUPPORTED_EXTENSIONS = "xlsx"

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        """Initialize reader with file contents."""
        # Read the Excel file - Diomni exports have a single sheet
        # Sheet name changed from "Target_Call" (v4.2.0) to "Target Call" (v4.3.0)
        sheet_name = self._get_sheet_name(named_file_contents.contents)
        df = read_excel(
            named_file_contents.contents,
            header=None,
            sheet_name=sheet_name,
            engine="calamine",
        )

        # Replace NaN with None for cleaner handling
        df = df.replace(np.nan, None)

        # Parse header section (metadata is in first column as key-value pairs)
        self.header = self._parse_header(df)

        # Parse measurements section
        self.measurements = self._parse_measurements(df)

    @staticmethod
    def _get_sheet_name(contents: IOType) -> str:
        """Determine the sheet name (changed between versions).

        v4.2.0 uses "Target_Call" (underscore)
        v4.3.0 uses "Target Call" (space)
        """
        # Note: pandas type stubs don't include 'calamine' engine yet, hence the type ignore
        excel_file = pd.ExcelFile(contents, engine="calamine")  # type: ignore[arg-type]

        # Try both possible sheet names
        if "Target_Call" in excel_file.sheet_names:
            return "Target_Call"
        elif "Target Call" in excel_file.sheet_names:
            return "Target Call"
        else:
            msg = f"Expected sheet 'Target_Call' or 'Target Call' not found. Available sheets: {excel_file.sheet_names}"
            raise ValueError(msg)

    def _parse_header(self, df: pd.DataFrame) -> SeriesData:
        """Parse header/metadata section.

        The header is in the first ~27 rows with format:
        Column 0: Key, Column 1: Value
        """
        # Find the row where data section starts (when first column is "Well")
        data_start_idx = None
        for idx, val in enumerate(df.iloc[:, 0]):
            if val == "Well":
                data_start_idx = idx
                break

        if data_start_idx is None:
            data_start_idx = 27  # Default fallback

        # Extract header rows
        header_df = df.iloc[:data_start_idx, :2].copy()
        header_df.columns = pd.Index(["key", "value"])

        # Drop rows where key is None
        header_df = header_df[header_df["key"].notna()]

        # Convert to series with keys as index
        header_series = header_df.set_index("key")["value"]

        return SeriesData(header_series)

    def _parse_measurements(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse measurement data.

        Data starts after metadata section with headers like:
        Well, Omit, Sample, Sample type, Target, Reporter, Call, Cq, etc.
        """
        # Find the row where data section starts (when first column is "Well")
        data_start_idx = None
        for idx, val in enumerate(df.iloc[:, 0]):
            if val == "Well":
                data_start_idx = idx
                break

        if data_start_idx is None:
            msg = "Unable to find data section starting with 'Well' column"
            raise ValueError(msg)

        # Extract data rows
        data = df.iloc[data_start_idx + 1 :].copy()

        # Set column names from the header row
        data.columns = pd.Index(df.iloc[data_start_idx].tolist())

        # Reset index
        data = data.reset_index(drop=True)

        # Drop completely empty rows
        data = data.dropna(how="all")

        return data
