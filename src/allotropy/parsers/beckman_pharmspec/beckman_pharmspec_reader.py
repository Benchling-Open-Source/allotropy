from io import BytesIO

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import parse_header_row, read_excel, SeriesData


class BeckmanPharmspecReader:
    SUPPORTED_EXTENSIONS = "xlsx,xls"
    data: pd.DataFrame
    header: SeriesData

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        if named_file_contents.extension == "xls":
            self._read_xls(named_file_contents)
        else:
            self._read_xlsx(named_file_contents)

    def _read_xlsx(self, named_file_contents: NamedFileContents) -> None:
        df = read_excel(named_file_contents.contents, header=None, engine="calamine")

        # Detect format: PharmSpec uses col1=":" with value in col2,
        # HIAC Run Counter uses col1=": value" (colon+value merged).
        is_pharmspec = df[1].str.strip().eq(":").any() if 1 in df.columns else False
        if not is_pharmspec:
            self._parse_hiac_run_counter_format(df)
            return

        """
        Find the data in the raw dataframe. We identify the boundary of the data
        by finding the index first row which contains the word 'Particle' and ending right before
        the index of the first row containing 'Approver'.
        """
        # Check for rows containing "Particle" in column 1
        particle_rows = df[df[1].str.contains("Particle", na=False)].index.values
        if len(particle_rows) == 0:
            msg = "Unable to find required 'Particle' marker in column 1 of the data file."
            raise AllotropeConversionError(msg)
        start = particle_rows[0]

        # Check for rows containing "Approver_" in column 0
        approver_rows = df[df[0].str.contains("Approver_", na=False)].index.values
        if len(approver_rows) == 0:
            msg = "Unable to find required 'Approver_' marker in column 0 of the data file."
            raise AllotropeConversionError(msg)
        end = approver_rows[0] - 1

        # The header data is everything up to the start of the data.
        # It is stored in two columns spread over the first 6 columns.
        raw_header = df.loc[: start - 1].T
        header_data = pd.concat([raw_header.loc[2], raw_header.loc[5]])
        header_columns = pd.concat([raw_header.loc[0], raw_header.loc[3]])

        # Store the software version string before filtering (it's usually at index 0)
        software_version_string = (
            str(header_data.iloc[0]) if len(header_data) > 0 else "Unknown"
        )

        # Filter out nan values from header_columns to avoid nan keys in the Series
        valid_mask = ~pd.isna(header_columns)
        header_data = header_data[valid_mask]
        header_columns = header_columns[valid_mask]

        header_data.index = pd.Index(header_columns)

        # Create a SeriesData with the software version string preserved
        series_data = SeriesData(header_data)
        series_data._software_version_string = software_version_string  # type: ignore
        self.header = series_data

        data = df.loc[start:end]
        data = parse_header_row(data)
        data["Run No."] = data["Run No."].ffill()
        self.data = data.dropna(subset="Particle Size(µm)")

    def _read_xls(self, named_file_contents: NamedFileContents) -> None:
        raw_content = named_file_contents.contents.read()
        content_bytes = (
            raw_content.encode("utf-8") if isinstance(raw_content, str) else raw_content
        )

        is_html = content_bytes.lstrip()[:6].lower().startswith(
            b"<html>"
        ) or content_bytes.lstrip()[:5].lower().startswith(b"<html")
        if is_html:
            self._read_xls_html(content_bytes)
        else:
            self._read_xls_binary(BytesIO(content_bytes))

    def _read_xls_binary(self, contents: BytesIO) -> None:
        df = read_excel(contents, header=None, engine="calamine")
        self._parse_hiac_run_counter_format(df)

    def _read_xls_html(self, content_bytes: bytes) -> None:
        tables = pd.read_html(content_bytes.decode("utf-8", errors="ignore"))

        # Combine header tables (tables 0 and 1) into a unified dataframe
        header_frames = []
        for table in tables[:-1]:
            if "Run No." in table.columns or (
                len(table.columns) == 6
                and any("Particle" in str(c) for c in table.iloc[0] if pd.notna(c))
            ):
                break
            header_frames.append(table)

        # Find the data table (has Run No. column or 6 columns with particle data)
        data_table = None
        for table in tables:
            cols = [str(c) for c in table.columns]
            if "Run No." in cols and "Particle Size(µm)" in cols:
                data_table = table
                break

        if data_table is None:
            msg = "Unable to find data table with 'Run No.' and 'Particle Size(µm)' columns in HTML file."
            raise AllotropeConversionError(msg)

        # Parse header from the header tables
        header_dict: dict[str, str] = {}
        for frame in header_frames:
            for _, row in frame.iterrows():
                values = [str(v) if pd.notna(v) else "" for v in row.values]
                # Process pairs: (key, ": value") pattern
                i = 0
                while i < len(values) - 1:
                    key = values[i].strip()
                    val = values[i + 1].strip()
                    if key and val.startswith(":"):
                        header_dict[key] = val[1:].strip()
                        i += 2
                    else:
                        i += 1

        header_series = pd.Series(header_dict)
        series_data = SeriesData(header_series)
        series_data._software_version_string = "Unknown"  # type: ignore
        self.header = series_data

        # Normalize the data table
        data_table["Run No."] = data_table["Run No."].ffill()
        self.data = data_table.dropna(subset="Particle Size(µm)")

    def _parse_hiac_run_counter_format(self, df: pd.DataFrame) -> None:
        """Parse the HIAC 'Run Counter Test' format from a binary XLS dataframe."""
        # Find the data header row containing "Particle Size"
        particle_rows = df[
            df.apply(
                lambda row: any(
                    "Particle" in str(v) for v in row.values if pd.notna(v)
                ),
                axis=1,
            )
        ].index.values
        if len(particle_rows) == 0:
            msg = "Unable to find 'Particle Size' header in the data file."
            raise AllotropeConversionError(msg)
        start = particle_rows[0]

        # Parse header from rows before the data table
        # Format: col0=key, col1=": value", col2=key, col3=": value"
        header_dict: dict[str, str] = {}
        for i in range(start):
            row = df.iloc[i]
            values = [str(v) if pd.notna(v) else "" for v in row.values]
            j = 0
            while j < len(values) - 1:
                key = values[j].strip()
                val = values[j + 1].strip()
                if key and val.startswith(":"):
                    header_dict[key] = val[1:].strip()
                    j += 2
                else:
                    j += 1

        header_series = pd.Series(header_dict)
        series_data = SeriesData(header_series)
        series_data._software_version_string = "Unknown"  # type: ignore
        self.header = series_data

        # Extract data section
        data = df.loc[start:]
        data = parse_header_row(data)
        data["Run No."] = data["Run No."].ffill()
        self.data = data.dropna(subset="Particle Size(µm)")
