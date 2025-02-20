from typing import ClassVar

from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_calculated_documents import (
    iter_primary_analysis_calc_docs,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.constants import (
    ExperimentType,
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
        wells = PrimaryAnalysisWellList.create(reader, header)
        well_items = wells.get_well_items()

        return Data(
            header,
            wells,
            experiment_type=ExperimentType.primary_analysis_experiment,
            calculated_documents=list(iter_primary_analysis_calc_docs(well_items)),
            reference_target=None,
            reference_sample=None,
        )
