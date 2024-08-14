from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    Data,
    Header,
    WellList,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.creators.generic import (
    Creator,
)


class MeltCurveCreator(Creator):
    EXPECTED_SHEETS = [
        "Melt Curve Raw",
        "Melt Curve Result",
    ]

    @classmethod
    def create(cls, contents: DesignQuantstudioContents) -> Data:
        header = Header.create(contents.header)
        wells = WellList.create(
            contents, header, ExperimentType.melt_curve_qPCR_experiment
        )
        return Data(
            header,
            wells,
            experiment_type=ExperimentType.melt_curve_qPCR_experiment,
            calculated_documents=[],
            reference_target=None,
            reference_sample=None,
        )
