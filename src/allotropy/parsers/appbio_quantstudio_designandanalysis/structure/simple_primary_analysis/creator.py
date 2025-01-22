from typing import ClassVar

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
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.simple_primary_analysis.structure import (
    SimplePrimaryAnalysisWellList,
)


class SimplePrimaryAnalysisCreator(Creator):
    PLUGIN_REGEX: ClassVar[str] = r"^Primary Analysis v\d+\.\d+\.\d+$"
    EXPECTED_SHEETS: ClassVar[list[str]] = ["Results"]

    @classmethod
    def check_sheets(cls, reader: DesignQuantstudioReader) -> bool:
        return list(reader.data.keys()) == cls.EXPECTED_SHEETS

    @classmethod
    def create(cls, reader: DesignQuantstudioReader) -> Data:
        header = Header.create(reader.header)
        wells = SimplePrimaryAnalysisWellList.create(reader, header)
        return Data(
            header,
            wells,
            experiment_type=ExperimentType.primary_analysis_experiment,
            calculated_documents=[],
            reference_target=None,
            reference_sample=None,
        )
