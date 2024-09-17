from dataclasses import dataclass

import pandas as pd

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Result,
    Well,
    WellItem,
    WellList,
)
from allotropy.parsers.utils.pandas import SeriesData


class PresenceAbsenceResult(Result):
    @classmethod
    def get_genotyping_determination_result(cls, target_data: SeriesData) -> str | None:
        return target_data.get(str, "Call")

    @classmethod
    def get_genotyping_determination_method_setting(
        cls, target_data: SeriesData
    ) -> float | None:
        return target_data.get(float, "Threshold")


class PresenceAbsenceWellItem(WellItem):
    @classmethod
    def get_result_class(cls) -> type[Result]:
        return PresenceAbsenceResult


class PresenceAbsenceWell(Well):
    @classmethod
    def get_well_item_class(cls) -> type[WellItem]:
        return PresenceAbsenceWellItem


@dataclass(frozen=True)
class PresenceAbsenceWellList(WellList):
    @classmethod
    def get_well_class(cls) -> type[Well]:
        return PresenceAbsenceWell

    @classmethod
    def get_well_result_data(cls, reader: DesignQuantstudioReader) -> pd.DataFrame:
        return cls._add_data(
            data=reader.get_non_empty_sheet(cls.get_data_sheet()),
            extra_data=reader.get_non_empty_sheet("Target Call"),
            columns=[
                "Call",
            ],
        )
