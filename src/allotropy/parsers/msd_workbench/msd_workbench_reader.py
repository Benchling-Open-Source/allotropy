import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv


class MSDWorkbenchReader:
    SUPPORTED_EXTENSIONS = "csv, txt, xlsx"
    plate_data: pd.DataFrame
    well_plate_id: str

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        if named_file_contents.extension == "xlsx":
            # Read the Workbench data sheet from Excel file
            data = pd.read_excel(
                named_file_contents.contents,
                sheet_name="Workbench data",
                engine="openpyxl",
            )
            data = data.where(pd.notna(data), None)
            data.index = pd.Index(data.index.to_series().ffill())
            data.index = data.index.astype(str).str.strip()
            data.columns = data.columns.astype(str).str.strip()
            first_row = str(data.iloc[0].index[0])
            if "Plate" not in first_row:
                msg = "Plate ID not found in the first row of the data"
                raise AllotropeConversionError(msg)
            self.well_plate_id = first_row.split("_")[-1].strip()
            # Set the first row as the header
            data.columns = pd.Index(data.iloc[0])
            data = data[1:].reset_index(drop=True)
        else:
            # First, peek at the first line to check format
            named_file_contents.contents.seek(0)
            first_line = named_file_contents.contents.readline()
            if isinstance(first_line, bytes):
                first_line = first_line.decode("utf-8")
            named_file_contents.contents.seek(0)

            # Check if first line has commas (old format) or not (new format)
            if "," in first_line:
                # Old format: Plate_ID,,,,,,,,
                data = read_csv(named_file_contents.contents)
                data = data.where(pd.notna(data), None)
                data.index = pd.Index(data.index.to_series().ffill())
                data.index = data.index.astype(str).str.strip()
                data.columns = data.columns.astype(str).str.strip()
                first_row = str(data.iloc[0].index[0])
                if "Plate" not in first_row:
                    msg = "Plate ID not found in the first row of the data"
                    raise AllotropeConversionError(msg)
                self.well_plate_id = first_row.split("_")[-1].strip()
                # Set the first row as the header
                data.columns = pd.Index(data.iloc[0])
                data = data[1:].reset_index(drop=True)
            else:
                # New format: Plate_ID (no commas on first line)
                # Extract plate ID from first line
                plate_id_line = first_line.strip()
                if "Plate" not in plate_id_line:
                    msg = "Plate ID not found in the first row of the data"
                    raise AllotropeConversionError(msg)
                self.well_plate_id = plate_id_line.split("_")[-1].strip()

                # Now read the CSV starting from the second line (which has headers)
                named_file_contents.contents.seek(0)
                # Skip the first line
                named_file_contents.contents.readline()
                # Read rest of file with second line as header
                data = read_csv(named_file_contents.contents)
                data = data.where(pd.notna(data), None)
                data.columns = data.columns.astype(str).str.strip()

        self.plate_data = data
