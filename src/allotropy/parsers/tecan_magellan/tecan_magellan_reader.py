import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_excel, split_dataframe
from allotropy.parsers.utils.values import assert_not_none


class TecanMagellanReader:
    SUPPORTED_EXTENSIONS = "xlsx"
    metadata: list[str]
    data: pd.DataFrame

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        data = read_excel(named_file_contents.contents)
        self.data, metadata = split_dataframe(
            data,
            lambda row: row.astype(str).iloc[0].startswith("Date of measurement"),
            include_split_row=True,
        )
        self.metadata = assert_not_none(metadata).iloc[:, 0].to_list()
