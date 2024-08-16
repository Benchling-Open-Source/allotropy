from dataclasses import dataclass

from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    WellList,
)


@dataclass(frozen=True)
class StandardCurveWellList(WellList):
    @classmethod
    def get_data_sheet(cls) -> str:
        return "Standard Curve Result"
