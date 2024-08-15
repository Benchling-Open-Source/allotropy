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
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.primary_analysis.structure import (
    PrimaryAnalysisWellList,
)


class PrimaryAnalysisCreator(Creator):
    @classmethod
    def check_type(cls, contents: DesignQuantstudioContents) -> bool:
        return list(contents.data.keys()) == ["Results"]

    @classmethod
    def create(cls, contents: DesignQuantstudioContents) -> Data:
        header = Header.create(contents.header)
        wells = PrimaryAnalysisWellList.create(contents, header)
        return Data(
            header,
            wells,
            experiment_type=ExperimentType.presence_absence_qPCR_experiment,
            calculated_documents=[],
            reference_target=None,
            reference_sample=None,
        )
