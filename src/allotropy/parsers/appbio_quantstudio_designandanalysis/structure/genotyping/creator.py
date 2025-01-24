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
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.genotyping.structure import (
    GenotypingWellList,
)


class GenotypingCreator(Creator):
    PLUGIN_REGEX: ClassVar[str] = r"Genotyping"
    EXPECTED_SHEETS: ClassVar[list[str]] = [
        "Genotyping Result",
    ]

    @classmethod
    def create(cls, reader: DesignQuantstudioReader) -> Data:
        header = Header.create(reader.header)
        wells = GenotypingWellList.create(reader, header)
        return Data(
            header,
            wells,
            experiment_type=ExperimentType.genotyping_qpcr_experiment,
            calculated_documents=[],
            reference_target=None,
            reference_sample=None,
        )
