import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import parse_header_row, read_excel, SeriesData


class BeckmanPharmspecReader:
    SUPPORTED_EXTENSIONS = "xlsx"
    data: pd.DataFrame
    header: SeriesData

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        df = read_excel(named_file_contents.contents, header=None, engine="calamine")

        """
        Find the data in the raw dataframe. We identify the boundary of the data
        by finding the index first row which contains the word 'Particle' and ending right before
        the index of the first row containing 'Approver'.
        """
        start = df[df[1].str.contains("Particle", na=False)].index.values[0]
        end = df[df[0].str.contains("Approver_", na=False)].index.values[0] - 1

        # The header data is everything up to the start of the data.
        # It is stored in two columns spread over the first 6 columns.
        raw_header = df.loc[: start - 1].T
        header_data = pd.concat([raw_header.loc[2], raw_header.loc[5]])
        header_columns = pd.concat([raw_header.loc[0], raw_header.loc[3]])
        header_data.index = pd.Index(header_columns)
        self.header = SeriesData(header_data)

        data = df.loc[start:end]
        data = parse_header_row(data)
        data["Run No."] = data["Run No."].ffill()
        self.data = data.dropna(subset="Particle Size(µm)")
