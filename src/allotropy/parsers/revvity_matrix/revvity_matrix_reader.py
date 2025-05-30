import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import (
    df_to_series_data,
    read_csv,
    read_excel,
    SeriesData,
)


class RevvityMatrixReader:
    SUPPORTED_EXTENSIONS = "csv,xlsx"
    data: pd.DataFrame
    headers: SeriesData

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        self.headers = SeriesData()

        if named_file_contents.extension == "csv":
            # Read the file normally
            df = read_csv(
                named_file_contents.contents, encoding=named_file_contents.encoding
            )
            # Check if this is the format with headers
            if self._has_header_format(df):
                self._extract_headers_and_data(df)
            else:
                df = df.dropna(axis=1, how="all")
                self.data = df

        else:
            df = read_excel(named_file_contents.contents)
            # Check if this is the format with headers
            if self._has_header_format(df):
                self._extract_headers_and_data(df)
            else:
                df = df.dropna(axis=1, how="all")
                self.data = df
                # For standard Excel format, fix viability if needed
                if "Viability" in df.columns:
                    # Reading a percent value (50%) in read_excel results in a decimal: 0.5
                    # Detect and adjust value back to 0-100%
                    first_row = df_to_series_data(df, 0)
                    viability = first_row[str, "Viability"]
                    if "%" not in first_row[str, "Viability"] and float(viability) < 1:
                        df["Viability"] = df["Viability"] * 100
                    first_row.get_unread()

    def _has_header_format(self, df: pd.DataFrame) -> bool:
        if len(df) > 0:
            cols = ",".join(map(str, df.columns))
            return "Plate Name" in cols
        return False

    def _extract_headers_and_data(self, df: pd.DataFrame) -> None:
        # Find where the data section starts (row with Row, Column)
        data_start_idx = None

        for i in range(len(df)):
            row_values = df.iloc[i].astype(str).tolist()
            row_str = ",".join([str(x) for x in row_values if pd.notna(x)])
            if "Row" in row_str and "Column" in row_str:
                data_start_idx = i
                break

        if data_start_idx is None:
            # If we can't find the proper markers, assume it's not a header format
            df = df.dropna(axis=1, how="all")
            self.data = df
            return

        # Extract column names first - these will be our first row of headers
        header_dict = {
            df.columns[0]: df.columns[1].split(":")[-1].strip()
            if ":" in df.columns[1]
            else df.columns[1]
        }

        # Extract headers from the rows above the data section
        for i in range(data_start_idx):
            row = df.iloc[i].tolist()
            if len(row) >= 2 and pd.notna(row[0]) and pd.notna(row[1]):
                key = str(row[0]).strip()
                value = str(row[1]).strip()
                if key in ["Dilution", "Assay Name"]:
                    value = value.split(":")[-1].strip() if ":" in value else value
                header_dict[key] = value

        clean_header_dict = {
            k: v for k, v in header_dict.items() if pd.notna(k) and pd.notna(v)
        }
        self.headers = SeriesData(pd.Series(clean_header_dict))

        # Extract the data section
        data_df = df.iloc[data_start_idx:].reset_index(drop=True)

        # Fix the type error by ensuring we convert the first row to column names properly
        first_row = data_df.iloc[0]
        # Convert the Series to a list of strings for the column names
        column_names = [str(x) for x in first_row.values]
        data_df.columns = pd.Index(column_names)

        data_df = data_df.iloc[1:].reset_index(drop=True)

        data_df = data_df.dropna(axis=1, how="all")
        self.data = data_df
