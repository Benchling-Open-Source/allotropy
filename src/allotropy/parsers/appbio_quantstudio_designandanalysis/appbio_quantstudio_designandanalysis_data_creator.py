from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ExperimentType
from allotropy.exceptions import AllotropeConversionError
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


def get_experiment_type(contents: DesignQuantstudioContents) -> ExperimentType:
    experiment_type_to_expected_sheets = {
        ExperimentType.standard_curve_qPCR_experiment: ["Standard Curve Result"],
        ExperimentType.relative_standard_curve_qPCR_experiment: [
            "RQ Replicate Group Result"
        ],
        ExperimentType.genotyping_qPCR_experiment: ["Genotyping Result"],
        ExperimentType.melt_curve_qPCR_experiment: [
            "Melt Curve Raw",
            "Melt Curve Result",
        ],
        ExperimentType.presence_absence_qPCR_experiment: [
            "Sample Call",
            "Well Call",
            "Target Call",
            "Control Status",
        ],
    }

    possible_experiment_types = {
        experiment_type
        for experiment_type, expected_sheets in experiment_type_to_expected_sheets.items()
        if all(contents.has_sheet(sheet_name) for sheet_name in expected_sheets)
    }

    if len(possible_experiment_types) == 1:
        return possible_experiment_types.pop()

    msg = f"Unable to infer experiment type from sheets in the input, expected exactly one set of sheets from: {list(experiment_type_to_expected_sheets.values())}, got {list(contents.data.keys())}"
    raise AllotropeConversionError(msg)


def create_data(contents: DesignQuantstudioContents) -> Data:
    experiment_type = get_experiment_type(contents)
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
