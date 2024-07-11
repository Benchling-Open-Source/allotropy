from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_calculated_documents import (
    iter_presence_absence_calc_docs,
    iter_relative_standard_curve_calc_docs,
    iter_standard_curve_calc_docs,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_contents import (
    DesignQuantstudioContents,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_structure import (
    Data,
    Header,
    Result,
    WellList,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_views import (
    SampleView,
    TargetRoleView,
    TargetView,
)


def create_data(contents: DesignQuantstudioContents) -> Data:
    experiment_type = Data.get_experiment_type(contents)
    header = Header.create(contents.header)
    wells = WellList.create(contents, header, experiment_type)
    well_items = wells.get_well_items()

    view_st_data = SampleView(sub_view=TargetView()).apply(well_items)
    r_sample = None
    r_target = None

    if experiment_type == ExperimentType.standard_curve_qPCR_experiment:
        calculated_documents = list(
            iter_standard_curve_calc_docs(
                view_st_data,
                view_tr_data=TargetRoleView().apply(well_items),
            )
        )
    elif experiment_type == ExperimentType.relative_standard_curve_qPCR_experiment:
        r_sample = Result.get_reference_sample(contents)
        r_target = Result.get_reference_target(contents)
        calculated_documents = list(
            iter_relative_standard_curve_calc_docs(
                view_st_data,
                r_sample,
                r_target,
            )
        )
    elif experiment_type == ExperimentType.presence_absence_qPCR_experiment:
        calculated_documents = list(
            iter_presence_absence_calc_docs(
                view_st_data,
            )
        )
    else:
        calculated_documents = []

    return Data(
        header,
        wells,
        experiment_type,
        calculated_documents,
        reference_target=r_target,
        reference_sample=r_sample,
    )
