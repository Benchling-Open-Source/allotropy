from typing import ClassVar

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.creator import (
    Creator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Data,
    Header,
    WellList,
)


class PrimaryAnalysisCreator(Creator):
    PLUGIN_REGEX: ClassVar[str] = r"^Primary Analysis v\d+\.\d+\.\d+$"
    EXPECTED_SHEETS: ClassVar[list[str]] = [
        "Results",
        "Amplification Data",
        "Multicomponent",
        "Replicate Group Result",
    ]

    @classmethod
    def create(cls, reader: DesignQuantstudioReader) -> Data:
        header = Header.create(reader.header)
        wells = WellList.create(reader, header)
        return Data(
            header,
            wells,
            experiment_type=ExperimentType.primary_analysis_experiment,
            calculated_documents=[],
            reference_target=None,
            reference_sample=None,
        )
