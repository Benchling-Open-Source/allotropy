import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_csv


class MSDWorkbenchReader:
    SUPPORTED_EXTENSIONS = "csv, txt"
    plate_data: pd.DataFrame
    well_plate_id: str

    def __init__(self, named_file_contents: NamedFileContents) -> None:
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
        self.plate_data = data
