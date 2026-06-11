from collections.abc import Iterator

from allotropy.calcdocs import (
    build_calc_docs,
    CalcDoc,
    Measurement,
    Node,
)
from allotropy.calcdocs.appbio_quantstudio_designandanalysis.extractor import (
    AppbioQuantstudioDAExtractor,
)
from allotropy.calcdocs.views import SampleView, TargetRoleView, TargetView, UuidView
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    WellItem,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)

CTR = Measurement(
    "cycle threshold result", field="cycle_threshold_result", required=True
)
NORM_REPORTER = Measurement(
    "normalized reporter result", field="normalized_reporter_result"
)

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
        "r^2", field="r_squared", sources=["cycle threshold result"], view="tdna_role"
    ),
    CalcDoc(
        "slope", field="slope", sources=["cycle threshold result"], view="tdna_role"
    ),
    CalcDoc(
        "efficiency",
        field="efficiency",
        sources=["cycle threshold result"],
        view="tdna_role",
    ),
    CalcDoc(
        "standard deviation",
        field="standard_deviation",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
    ),
    CalcDoc(
        "standard error",
        field="standard_error",
        sources=["cycle threshold result"],
        view="sid_tdna_uuid",
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
        "ct mean", field="ct_mean", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "ct sd", field="ct_sd", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "ct sd @ref",
        field="ct_sd",
        sources=["cycle threshold result"],
        view="sid_tdna_ref",
        source_only=True,
        output_name="ct sd",
    ),
    CalcDoc(
        "ct se",
        field="ct_se",
        sources=["cycle threshold result"],
        view="sid_tdna",
        source_only=True,
    ),
    CalcDoc(
        "ct se @ref",
        field="ct_se",
        sources=["cycle threshold result"],
        view="sid_tdna_ref",
        source_only=True,
        output_name="ct se",
    ),
    CalcDoc(
        "delta equivalent ct sd",
        field="delta_ct_sd",
        sources=["ct sd", "ct sd @ref"],
        view="sid_tdna",
    ),
    CalcDoc(
        "delta equivalent ct se",
        field="delta_ct_se",
        sources=["ct se", "ct se @ref"],
        view="sid_tdna",
    ),
    CalcDoc(
        "quantity mean",
        field="quantity_mean",
        sources=["quantity"],
        view="sid_tdna",
        source_only=True,
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
    # Deep dependency chain for rq_min/rq_max
    CalcDoc(
        "equivalent ct mean",
        field="eq_ct_mean",
        sources=["ct mean"],
        view="sid_tdna",
        source_only=True,
    ),
    CalcDoc(
        "adjusted equivalent ct mean",
        field="adj_eq_ct_mean",
        sources=["equivalent ct mean"],
        view="sid_tdna",
        source_only=True,
        optional=True,
    ),
    CalcDoc(
        "adjusted equivalent ct mean @ref",
        field="adj_eq_ct_mean",
        sources=["equivalent ct mean"],
        view="sid_tdna_ref",
        source_only=True,
        optional=True,
        output_name="adjusted equivalent ct mean",
    ),
    CalcDoc(
        "delta equivalent ct mean",
        field="delta_ct_mean",
        sources=["adjusted equivalent ct mean", "adjusted equivalent ct mean @ref"],
        view="sid_tdna",
        source_only=True,
    ),
    CalcDoc(
        "delta equivalent ct mean @ref_sample",
        field="delta_ct_mean",
        sources=["adjusted equivalent ct mean", "adjusted equivalent ct mean @ref"],
        view="sid_ref_tdna",
        source_only=True,
        output_name="delta equivalent ct mean",
    ),
    CalcDoc(
        "delta delta equivalent ct",
        field="delta_delta_ct",
        sources=["delta equivalent ct mean", "delta equivalent ct mean @ref_sample"],
        view="sid_tdna",
        source_only=True,
    ),
    CalcDoc(
        "rq",
        field="rq",
        sources=["delta delta equivalent ct"],
        view="sid_tdna",
        source_only=True,
    ),
    CalcDoc("rq min", field="rq_min", sources=["rq"], view="sid_tdna_blacklist"),
    CalcDoc("rq max", field="rq_max", sources=["rq"], view="sid_tdna_blacklist"),
    # Standalone top-level nodes
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

PRIMARY_ANALYSIS_NODES: list[Node] = [
    CTR,
    CalcDoc(
        "ct mean", field="ct_mean", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "ct sd", field="ct_sd", sources=["cycle threshold result"], view="sid_tdna"
    ),
    CalcDoc(
        "ct se", field="ct_se", sources=["cycle threshold result"], view="sid_tdna"
    ),
]


def iter_standard_curve_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    elements = AppbioQuantstudioDAExtractor.get_elements(well_items)
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
    r_sample: str | None,
    r_target: str | None,
) -> Iterator[CalculatedDocument]:
    elements = AppbioQuantstudioDAExtractor.get_elements(well_items)
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
    yield from build_calc_docs(nodes=RELATIVE_STANDARD_CURVE_NODES, views=views)


def iter_presence_absence_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    elements = AppbioQuantstudioDAExtractor.get_elements(well_items)
    views = {
        "sid_tdna": SampleView(sub_view=TargetView()).apply(elements),
        "sid_tdna_uuid": SampleView(sub_view=TargetView(sub_view=UuidView())).apply(
            elements
        ),
    }
    yield from build_calc_docs(nodes=PRESENCE_ABSENCE_NODES, views=views)


def iter_primary_analysis_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    elements = AppbioQuantstudioDAExtractor.get_elements(well_items)
    views = {
        "sid_tdna": SampleView(sub_view=TargetView()).apply(elements),
    }
    yield from build_calc_docs(nodes=PRIMARY_ANALYSIS_NODES, views=views)
