from collections.abc import Iterator

from allotropy.calcdocs import (
    build_calc_docs,
    CalcDoc,
    Measurement,
    Node,
)
from allotropy.calcdocs.appbio_quantstudio.extractor import AppbioQuantstudioExtractor
from allotropy.calcdocs.views import SampleView, TargetRoleView, TargetView, UuidView
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    WellItem,
)
from allotropy.parsers.appbio_quantstudio.constants import ExperimentType
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.values import assert_not_none

CTR = Measurement("cycle threshold result", field="cycle_threshold_result")
NORM_REPORTER = Measurement(
    "normalized reporter result", field="normalized_reporter_result"
)

COMPARATIVE_CT_NODES: list[Node] = [
    CTR,
    CalcDoc(
        "y intercept",
        field="y_intercept",
        sources=["cycle threshold result"],
        view="tdna_role",
        source_only=True,
    ),
    CalcDoc(
        "slope",
        field="slope",
        sources=["cycle threshold result"],
        view="tdna_role",
        source_only=True,
    ),
    CalcDoc(
        "quantity",
        field="quantity",
        sources=["cycle threshold result", "y intercept", "slope"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "amplification score",
        field="amp_score",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "cq confidence",
        field="cq_conf",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "quantity mean", field="quantity_mean", sources=["quantity"], view="sid_tdna"
    ),
    CalcDoc("quantity sd", field="quantity_sd", sources=["quantity"], view="sid_tdna"),
    CalcDoc(
        "ct mean", field="ct_mean", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "ct sd", field="ct_sd", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "ct mean @ref",
        field="ct_mean",
        sources=["cycle threshold result"],
        view="sid_tdna_ref",
        source_only=True,
        output_name="ct mean",
    ),
    CalcDoc(
        "delta ct se",
        field="delta_ct_se",
        sources=["ct mean", "ct mean @ref"],
        view="sid_tdna",
    ),
    CalcDoc(
        "delta ct mean",
        field="delta_ct_mean",
        sources=["ct mean", "ct mean @ref"],
        view="sid_tdna",
        source_only=True,
    ),
    CalcDoc(
        "delta ct mean @ref_sample",
        field="delta_ct_mean",
        sources=["ct mean", "ct mean @ref"],
        view="sid_ref_tdna",
        source_only=True,
        output_name="delta ct mean",
    ),
    CalcDoc(
        "delta delta ct",
        field="delta_delta_ct",
        sources=["delta ct mean", "delta ct mean @ref_sample"],
        view="sid_tdna",
        source_only=True,
    ),
    CalcDoc(
        "rq", field="rq", sources=["delta delta ct"], view="sid_tdna", source_only=True
    ),
    CalcDoc("rq min", field="rq_min", sources=["rq"], view="sid_tdna_blacklist"),
    CalcDoc("rq max", field="rq_max", sources=["rq"], view="sid_tdna_blacklist"),
]

STANDARD_CURVE_NODES: list[Node] = [
    CTR,
    CalcDoc(
        "quantity",
        field="quantity",
        sources=["cycle threshold result", "y intercept", "slope"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "amplification score",
        field="amp_score",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "cq confidence",
        field="cq_conf",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "quantity mean", field="quantity_mean", sources=["quantity"], view="sid_tdna"
    ),
    CalcDoc("quantity sd", field="quantity_sd", sources=["quantity"], view="sid_tdna"),
    CalcDoc(
        "ct mean", field="ct_mean", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "ct sd", field="ct_sd", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "y intercept",
        field="y_intercept",
        sources=["cycle threshold result"],
        view="tdna_role",
    ),
    CalcDoc(
        "slope", field="slope", sources=["cycle threshold result"], view="tdna_role"
    ),
    CalcDoc(
        "r^2", field="r_squared", sources=["cycle threshold result"], view="tdna_role"
    ),
    CalcDoc(
        "efficiency",
        field="efficiency",
        sources=["cycle threshold result"],
        view="tdna_role",
    ),
]

RELATIVE_STANDARD_CURVE_NODES: list[Node] = [
    CTR,
    CalcDoc(
        "quantity",
        field="quantity",
        sources=["cycle threshold result", "y intercept", "slope"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "amplification score",
        field="amp_score",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "cq confidence",
        field="cq_conf",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "quantity mean", field="quantity_mean", sources=["quantity"], view="sid_tdna"
    ),
    CalcDoc("quantity sd", field="quantity_sd", sources=["quantity"], view="sid_tdna"),
    CalcDoc(
        "ct mean", field="ct_mean", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "ct sd", field="ct_sd", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "relative rq",
        field="rq",
        sources=["quantity mean"],
        view="sid_tdna",
        source_only=True,
    ),
    CalcDoc(
        "relative rq min", field="rq_min", sources=["relative rq"], view="sid_tdna"
    ),
    CalcDoc(
        "relative rq max", field="rq_max", sources=["relative rq"], view="sid_tdna"
    ),
    CalcDoc(
        "y intercept",
        field="y_intercept",
        sources=["cycle threshold result"],
        view="tdna_role",
    ),
    CalcDoc(
        "slope", field="slope", sources=["cycle threshold result"], view="tdna_role"
    ),
    CalcDoc(
        "r^2", field="r_squared", sources=["cycle threshold result"], view="tdna_role"
    ),
    CalcDoc(
        "efficiency",
        field="efficiency",
        sources=["cycle threshold result"],
        view="tdna_role",
    ),
]

PRESENCE_ABSENCE_NODES: list[Node] = [
    CTR,
    NORM_REPORTER,
    CalcDoc(
        "quantity",
        field="quantity",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "amplification score",
        field="amp_score",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "cq confidence",
        field="cq_conf",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "rn mean",
        field="rn_mean",
        sources=["normalized reporter result"],
        view="sid_tdna",
    ),
    CalcDoc(
        "rn sd", field="rn_sd", sources=["normalized reporter result"], view="sid_tdna"
    ),
]


def iter_comparative_ct_calc_docs(
    well_items: list[WellItem],
    r_sample: str,
    r_target: str,
) -> Iterator[CalculatedDocument]:
    elements = AppbioQuantstudioExtractor.get_elements(well_items)
    views = {
        "sid_tdna": SampleView(sub_view=TargetView()).apply(elements),
        "sid_tdna_uuid": SampleView(sub_view=TargetView(sub_view=UuidView())).apply(
            elements
        ),
        "sid_ref_tdna": SampleView(reference=r_sample, sub_view=TargetView()).apply(
            elements
        ),
        "sid_tdna_ref": SampleView(
            sub_view=TargetView(is_reference=True, reference=r_target)
        ).apply(elements),
        "sid_tdna_blacklist": SampleView(
            sub_view=TargetView(blacklist=[r_target] if r_target is not None else None)
        ).apply(elements),
        "tdna_role": TargetRoleView().apply(elements),
    }
    yield from build_calc_docs(nodes=COMPARATIVE_CT_NODES, views=views)


def iter_standard_curve_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    elements = AppbioQuantstudioExtractor.get_elements(well_items)
    views = {
        "sid_tdna": SampleView(sub_view=TargetView()).apply(elements),
        "sid_tdna_uuid": SampleView(sub_view=TargetView(sub_view=UuidView())).apply(
            elements
        ),
        "tdna_role": TargetRoleView().apply(elements),
    }
    yield from build_calc_docs(nodes=STANDARD_CURVE_NODES, views=views)


def iter_relative_standard_curve_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    elements = AppbioQuantstudioExtractor.get_elements(well_items)
    views = {
        "sid_tdna": SampleView(sub_view=TargetView()).apply(elements),
        "sid_tdna_uuid": SampleView(sub_view=TargetView(sub_view=UuidView())).apply(
            elements
        ),
        "tdna_role": TargetRoleView().apply(elements),
    }
    yield from build_calc_docs(nodes=RELATIVE_STANDARD_CURVE_NODES, views=views)


def iter_presence_absence_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    elements = AppbioQuantstudioExtractor.get_elements(well_items)
    views = {
        "sid_tdna": SampleView(sub_view=TargetView()).apply(elements),
        "sid_tdna_uuid": SampleView(sub_view=TargetView(sub_view=UuidView())).apply(
            elements
        ),
    }
    yield from build_calc_docs(nodes=PRESENCE_ABSENCE_NODES, views=views)


def iter_calculated_data_documents(
    well_items: list[WellItem],
    experiment_type: ExperimentType,
    r_sample: str | None,
    r_target: str | None,
) -> Iterator[CalculatedDocument]:
    well_items = [well_item for well_item in well_items if well_item.has_result]

    if experiment_type == ExperimentType.relative_standard_curve_qpcr_experiment:
        yield from iter_relative_standard_curve_calc_docs(well_items)
    elif experiment_type == ExperimentType.comparative_ct_qpcr_experiment:
        yield from iter_comparative_ct_calc_docs(
            well_items,
            assert_not_none(r_sample),
            assert_not_none(r_target),
        )
    elif experiment_type == ExperimentType.standard_curve_qpcr_experiment:
        yield from iter_standard_curve_calc_docs(well_items)
    elif experiment_type == ExperimentType.presence_absence_qpcr_experiment:
        yield from iter_presence_absence_calc_docs(well_items)
