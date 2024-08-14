from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_calculated_documents import (
    iter_standard_curve_calc_docs,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    Data,
    Header,
    WellList,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_views import (
    SampleView,
    TargetRoleView,
    TargetView,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.creators.generic import (
    Creator,
)


class StandardCurveCreator(Creator):
    EXPECTED_SHEETS = [
        "Standard Curve Result",
    ]

    @classmethod
    def create(cls, contents: DesignQuantstudioContents) -> Data:
        header = Header.create(contents.header)
        wells = WellList.create(
            contents, header, ExperimentType.standard_curve_qPCR_experiment
        )
        well_items = wells.get_well_items()

        return Data(
            header,
            wells,
            experiment_type=ExperimentType.standard_curve_qPCR_experiment,
            calculated_documents=list(
                iter_standard_curve_calc_docs(
                    view_st_data=SampleView(sub_view=TargetView()).apply(well_items),
                    view_tr_data=TargetRoleView().apply(well_items),
                )
            ),
            reference_target=None,
            reference_sample=None,
        )
