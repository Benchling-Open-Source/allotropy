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
from allotropy.parsers.utils.values import assert_not_none


class GenotypingResult(Result):
    @classmethod
    def get_genotyping_determination_result(cls, target_data: SeriesData) -> str | None:
        return target_data.get(str, "Call")

    @classmethod
    def get_genotyping_determination_method_setting(
        cls, target_data: SeriesData
    ) -> float | None:
        return target_data.get(float, "Threshold")


class GenotypingWellItem(WellItem):
    @classmethod
    def get_result_class(cls) -> type[Result]:
        return GenotypingResult


class GenotypingWell(Well):
    @classmethod
    def get_well_item_class(cls) -> type[WellItem]:
        return GenotypingWellItem


@dataclass(frozen=True)
class GenotypingWellList(WellList):
    @classmethod
    def get_well_class(cls) -> type[Well]:
        return GenotypingWell

    @classmethod
    def get_well_result_data(cls, reader: DesignQuantstudioReader) -> pd.DataFrame:
        data = reader.get_non_empty_sheet(cls.get_data_sheet())
        genotyping_result = reader.get_non_empty_sheet("Genotyping Result")

        # The genotyping result data does not contain a target column
        # it can be constructed concatenating SNP assay column and the strings Allele 1/2
        rows = []
        for idx, row in genotyping_result.iterrows():
            snp_assay = assert_not_none(
                row.get("SNP Assay"),
                msg=f"Unable to get SNP Assay from Genotyping Result row '{idx}'.",
            )
            for allele in ["Allele 1", "Allele 2"]:
                new_row = row.copy()
                new_row["Target"] = f"{snp_assay}-{allele}"
                rows.append(new_row)

        return cls._add_data(
            data,
            extra_data=pd.DataFrame(rows).reset_index(drop=True),
            columns=[
                "Call",
            ],
        )
