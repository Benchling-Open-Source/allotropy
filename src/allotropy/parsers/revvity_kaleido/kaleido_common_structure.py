from dataclasses import dataclass


@dataclass(frozen=True)
class WellPosition:
    column: str
    row: str
