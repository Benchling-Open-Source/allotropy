from dataclasses import dataclass

import pandas as pd

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    WellList,
)
from allotropy.parsers.utils.values import assert_not_none


@dataclass(frozen=True)
class GenotypingWellList(WellList):
    @classmethod
    def get_well_result_data(cls, contents: DesignQuantstudioContents) -> pd.DataFrame:
        data = contents.get_non_empty_sheet(cls.get_data_sheet())
        genotyping_result = contents.get_non_empty_sheet("Genotyping Result")

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
