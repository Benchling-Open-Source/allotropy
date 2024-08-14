from typing import ClassVar

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_calculated_documents import (
    iter_presence_absence_calc_docs,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
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
        "Sample Call",
        "Well Call",
        "Target Call",
        "Control Status",
    ]

    @classmethod
    def create(cls, contents: DesignQuantstudioContents) -> Data:
        header = Header.create(contents.header)
        wells = PresenceAbsenceWellList.create(contents, header)
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
