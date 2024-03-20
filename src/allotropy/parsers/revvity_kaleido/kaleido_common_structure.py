from dataclasses import dataclass


@dataclass(frozen=True)
class WellPosition:
    column: str
    row: str

    def __repr__(self) -> str:
        return self.row + self.column
