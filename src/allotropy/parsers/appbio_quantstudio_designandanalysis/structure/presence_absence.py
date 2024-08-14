from dataclasses import dataclass

import pandas as pd

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    WellList,
)


@dataclass(frozen=True)
class PresenceAbsenceWellList(WellList):
    @classmethod
    def get_well_result_data(cls, contents: DesignQuantstudioContents) -> pd.DataFrame:
        return cls._add_data(
            data=contents.get_non_empty_sheet(cls.get_data_sheet()),
            extra_data=contents.get_non_empty_sheet("Target Call"),
            columns=[
                "Call",
            ],
        )
