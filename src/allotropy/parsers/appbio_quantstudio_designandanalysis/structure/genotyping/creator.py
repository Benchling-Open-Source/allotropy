from typing import ClassVar

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.creator import (
    Creator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Data,
    Header,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.genotyping.structure import (
    GenotypingWellList,
)


class GenotypingCreator(Creator):
    EXPECTED_SHEETS: ClassVar[list[str]] = [
        "Genotyping Result",
    ]

    @classmethod
    def create(cls, contents: DesignQuantstudioContents) -> Data:
        header = Header.create(contents.header)
        wells = GenotypingWellList.create(contents, header)
        return Data(
            header,
            wells,
            experiment_type=ExperimentType.genotyping_qPCR_experiment,
            calculated_documents=[],
            reference_target=None,
            reference_sample=None,
        )
