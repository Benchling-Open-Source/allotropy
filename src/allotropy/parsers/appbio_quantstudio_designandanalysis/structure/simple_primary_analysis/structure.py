from dataclasses import dataclass

import pandas as pd

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Well,
    WellItem,
    WellList,
)
from allotropy.parsers.utils.pandas import (
    assert_df_column,
)


@dataclass
class SimplePrimaryAnalysisWellItem(WellItem):
    @classmethod
    def get_amplification_data_sheet(
        cls, reader: DesignQuantstudioReader
    ) -> pd.DataFrame | None:
        return reader.get_non_empty_sheet_or_none("Amplification Data")


@dataclass
class SimplePrimaryAnalysisWell(Well):
    @classmethod
    def get_well_item_class(cls) -> type[WellItem]:
        return SimplePrimaryAnalysisWellItem


@dataclass(frozen=True)
class SimplePrimaryAnalysisWellList(WellList):
    @classmethod
    def get_well_class(cls) -> type[Well]:
        return SimplePrimaryAnalysisWell

    @classmethod
    def get_well_result_data(cls, reader: DesignQuantstudioReader) -> pd.DataFrame:
        results_data = super(  # noqa: UP008
            SimplePrimaryAnalysisWellList, cls
        ).get_well_result_data(reader)

        if "Well" not in results_data:
            pos = assert_df_column(results_data, "Well Position")
            pos_to_id = {p: i for i, p in enumerate(pos.unique(), start=1)}
            results_data["Well"] = [pos_to_id[pos] for pos in pos]

        if "Target" not in results_data:
            results_data["Target"] = "N/A"

        return results_data
