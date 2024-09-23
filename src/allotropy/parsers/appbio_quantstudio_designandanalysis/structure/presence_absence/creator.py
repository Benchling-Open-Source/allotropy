from typing import ClassVar

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_calculated_documents import (
    iter_presence_absence_calc_docs,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_views import (
    SampleView,
    TargetView,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.creator import (
    Creator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Data,
    Header,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.presence_absence.structure import (
    PresenceAbsenceWellList,
)


class PresenceAbsenceCreator(Creator):
    EXPECTED_SHEETS: ClassVar[list[str]] = [
        "Target Call",
    ]

    @classmethod
    def create(cls, reader: DesignQuantstudioReader) -> Data:
        header = Header.create(reader.header)
        wells = PresenceAbsenceWellList.create(reader, header)
        well_items = wells.get_well_items()
        return Data(
            header,
            wells,
            experiment_type=ExperimentType.presence_absence_qPCR_experiment,
            calculated_documents=list(
                iter_presence_absence_calc_docs(
                    view_data=SampleView(sub_view=TargetView()).apply(well_items),
                )
            ),
            reference_target=None,
            reference_sample=None,
        )
