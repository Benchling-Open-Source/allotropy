from typing import ClassVar

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_calculated_documents import (
    iter_relative_standard_curve_calc_docs,
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
    Result,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.relative_standard_curve.structure import (
    RelativeStandardCurveWellList,
)


class RelativeStandardCurveCreator(Creator):
    EXPECTED_SHEETS: ClassVar[list[str]] = [
        "RQ Replicate Group Result",
    ]

    @classmethod
    def create(cls, contents: DesignQuantstudioContents) -> Data:
        header = Header.create(contents.header)
        wells = RelativeStandardCurveWellList.create(contents, header)
        well_items = wells.get_well_items()

        r_sample = Result.get_reference_sample(contents)
        r_target = Result.get_reference_target(contents)

        return Data(
            header,
            wells,
            experiment_type=ExperimentType.relative_standard_curve_qPCR_experiment,
            calculated_documents=list(
                iter_relative_standard_curve_calc_docs(
                    view_data=SampleView(sub_view=TargetView()).apply(well_items),
                    r_sample=r_sample,
                    r_target=r_target,
                )
            ),
            reference_target=r_target,
            reference_sample=r_sample,
        )
