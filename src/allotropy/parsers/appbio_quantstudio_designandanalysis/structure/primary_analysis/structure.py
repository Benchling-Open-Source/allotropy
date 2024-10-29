from dataclasses import dataclass

import pandas as pd

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    WellList,
)


@dataclass(frozen=True)
class PrimaryAnalysisWellList(WellList):
    @classmethod
    def get_well_result_data(cls, reader: DesignQuantstudioReader) -> pd.DataFrame:
        return cls._add_data(
            data=reader.get_non_empty_sheet(cls.get_data_sheet()),
            extra_data=reader.get_non_empty_sheet("Replicate Group Result"),
            columns=[
                "Cq Mean",
                "Cq SD",
                "Cq SE",
            ],
        )
