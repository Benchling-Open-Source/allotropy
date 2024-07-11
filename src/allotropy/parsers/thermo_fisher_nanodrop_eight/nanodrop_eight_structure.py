


from dataclasses import dataclass


@dataclass
class SpectroscopyRow:
    row_data: pd.Series

    def create(row_data: pd.Series):
        return SpectroscopyRow(row_data)
