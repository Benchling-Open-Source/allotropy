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
    WellList,
)


class MeltCurveCreator(Creator):
    EXPECTED_SHEETS: ClassVar[list[str]] = [
        "Melt Curve Raw",
        "Melt Curve Result",
    ]

    @classmethod
    def check_plugin_name(cls, _: str | None) -> bool:
        return True

    @classmethod
    def create(cls, reader: DesignQuantstudioReader) -> Data:
        header = Header.create(reader.header)
        wells = WellList.create(reader, header)
        return Data(
            header,
            wells,
            experiment_type=ExperimentType.melt_curve_qpcr_experiment,
            calculated_documents=[],
            reference_target=None,
            reference_sample=None,
        )
