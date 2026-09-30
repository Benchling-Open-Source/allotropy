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


def _standard_curve_nodes() -> list[Node]:
    y_intercept = CalcDoc(
        "y intercept",
        field="y_intercept",
        sources=[CTR],
        view="tdna_role",
    )
    slope = CalcDoc("slope", field="slope", sources=[CTR], view="tdna_role")
    quantity = CalcDoc(
        "quantity",
        field="quantity",
        sources=[CTR, y_intercept, slope],
        view="sid_tdna_uuid",
    )
    amp_score = CalcDoc(
        "amplification score",
        field="amp_score",
        sources=[CTR],
        view="sid_tdna_uuid",
    )
    cq_conf = CalcDoc(
        "cq confidence",
        field="cq_conf",
        sources=[CTR],
        view="sid_tdna_uuid",
    )
    quantity_mean = CalcDoc(
        "quantity mean", field="quantity_mean", sources=[quantity], view="sid_tdna"
    )
    quantity_sd = CalcDoc(
        "quantity sd", field="quantity_sd", sources=[quantity], view="sid_tdna"
    )
    ct_mean = CalcDoc("ct mean", field="ct_mean", sources=[CTR], view="sid_tdna")
    ct_sd = CalcDoc("ct sd", field="ct_sd", sources=[CTR], view="sid_tdna")
    r_squared = CalcDoc("r^2", field="r_squared", sources=[CTR], view="tdna_role")
    efficiency = CalcDoc(
        "efficiency",
        field="efficiency",
        sources=[CTR],
        view="tdna_role",
    )
    standard_deviation = CalcDoc(
        "standard deviation",
        field="standard_deviation",
        sources=[CTR],
        view="sid_tdna_uuid",
    )
    standard_error = CalcDoc(
        "standard error",
        field="standard_error",
        sources=[CTR],
        view="sid_tdna_uuid",
    )
    return [
        CTR,
        quantity,
        amp_score,
        cq_conf,
        quantity_mean,
        quantity_sd,
        ct_mean,
        ct_sd,
        y_intercept,
        r_squared,
        slope,
        efficiency,
        standard_deviation,
        standard_error,
    ]


STANDARD_CURVE_NODES: list[Node] = _standard_curve_nodes()


def _relative_standard_curve_nodes() -> list[Node]:
    y_intercept = CalcDoc(
        "y intercept",
        field="y_intercept",
        sources=[CTR],
        view="tdna_role",
        source_only=True,
    )
    slope = CalcDoc(
        "slope",
        field="slope",
        sources=[CTR],
        view="tdna_role",
        source_only=True,
    )
    quantity = CalcDoc(
        "quantity",
        field="quantity",
        sources=[CTR, y_intercept, slope],
        view="sid_tdna_uuid",
    )
    amp_score = CalcDoc(
        "amplification score",
        field="amp_score",
        sources=[CTR],
        view="sid_tdna_uuid",
    )
    cq_conf = CalcDoc(
        "cq confidence",
        field="cq_conf",
        sources=[CTR],
        view="sid_tdna_uuid",
    )
    ct_mean = CalcDoc("ct mean", field="ct_mean", sources=[CTR], view="sid_tdna")
    ct_sd = CalcDoc("ct sd", field="ct_sd", sources=[CTR], view="sid_tdna")
    ct_sd_ref = CalcDoc(
        "ct sd",
        field="ct_sd",
        sources=[CTR],
        view="sid_tdna_ref",
        source_only=True,
    )
    ct_se = CalcDoc(
        "ct se",
        field="ct_se",
        sources=[CTR],
        view="sid_tdna",
        source_only=True,
    )
    ct_se_ref = CalcDoc(
        "ct se",
        field="ct_se",
        sources=[CTR],
        view="sid_tdna_ref",
        source_only=True,
    )
    delta_equivalent_ct_sd = CalcDoc(
        "delta equivalent ct sd",
        field="delta_ct_sd",
        sources=[ct_sd, ct_sd_ref],
        view="sid_tdna",
    )
    delta_equivalent_ct_se = CalcDoc(
        "delta equivalent ct se",
        field="delta_ct_se",
        sources=[ct_se, ct_se_ref],
        view="sid_tdna",
    )
    quantity_mean = CalcDoc(
        "quantity mean",
        field="quantity_mean",
        sources=[quantity],
        view="sid_tdna",
        source_only=True,
    )
    relative_rq = CalcDoc(
        "relative rq",
        field="rq",
        sources=[quantity_mean],
        view="sid_tdna",
        source_only=True,
    )
    relative_rq_min = CalcDoc(
        "relative rq min", field="rq_min", sources=[relative_rq], view="sid_tdna"
    )
    relative_rq_max = CalcDoc(
        "relative rq max", field="rq_max", sources=[relative_rq], view="sid_tdna"
    )
    # Deep dependency chain for rq_min/rq_max
    equivalent_ct_mean = CalcDoc(
        "equivalent ct mean",
        field="eq_ct_mean",
        sources=[ct_mean],
        view="sid_tdna",
        source_only=True,
    )
    adjusted_equivalent_ct_mean = CalcDoc(
        "adjusted equivalent ct mean",
        field="adj_eq_ct_mean",
        sources=[equivalent_ct_mean],
        view="sid_tdna",
        source_only=True,
        optional=True,
    )
    adjusted_equivalent_ct_mean_ref = CalcDoc(
        "adjusted equivalent ct mean",
        field="adj_eq_ct_mean",
        sources=[equivalent_ct_mean],
        view="sid_tdna_ref",
        source_only=True,
        optional=True,
    )
    delta_equivalent_ct_mean = CalcDoc(
        "delta equivalent ct mean",
        field="delta_ct_mean",
        sources=[adjusted_equivalent_ct_mean, adjusted_equivalent_ct_mean_ref],
        view="sid_tdna",
        source_only=True,
    )
    delta_equivalent_ct_mean_ref_sample = CalcDoc(
        "delta equivalent ct mean",
        field="delta_ct_mean",
        sources=[adjusted_equivalent_ct_mean, adjusted_equivalent_ct_mean_ref],
        view="sid_ref_tdna",
        source_only=True,
    )
    delta_delta_equivalent_ct = CalcDoc(
        "delta delta equivalent ct",
        field="delta_delta_ct",
        sources=[delta_equivalent_ct_mean, delta_equivalent_ct_mean_ref_sample],
        view="sid_tdna",
        source_only=True,
    )
    rq = CalcDoc(
        "rq",
        field="rq",
        sources=[delta_delta_equivalent_ct],
        view="sid_tdna",
        source_only=True,
    )
    rq_min = CalcDoc("rq min", field="rq_min", sources=[rq], view="sid_tdna_blacklist")
    rq_max = CalcDoc("rq max", field="rq_max", sources=[rq], view="sid_tdna_blacklist")
    return [
        CTR,
        quantity,
        amp_score,
        cq_conf,
        ct_mean,
        ct_sd,
        ct_sd_ref,
        ct_se,
        ct_se_ref,
        delta_equivalent_ct_sd,
        delta_equivalent_ct_se,
        quantity_mean,
        relative_rq,
        relative_rq_min,
        relative_rq_max,
        equivalent_ct_mean,
        adjusted_equivalent_ct_mean,
        adjusted_equivalent_ct_mean_ref,
        delta_equivalent_ct_mean,
        delta_equivalent_ct_mean_ref_sample,
        delta_delta_equivalent_ct,
        rq,
        rq_min,
        rq_max,
        y_intercept,
        slope,
    ]


RELATIVE_STANDARD_CURVE_NODES: list[Node] = _relative_standard_curve_nodes()


def _presence_absence_nodes() -> list[Node]:
    quantity = CalcDoc(
        "quantity",
        field="quantity",
        sources=[CTR],
        view="sid_tdna_uuid",
    )
    amp_score = CalcDoc(
        "amplification score",
        field="amp_score",
        sources=[CTR],
        view="sid_tdna_uuid",
    )
    cq_conf = CalcDoc(
        "cq confidence",
        field="cq_conf",
        sources=[CTR],
        view="sid_tdna_uuid",
    )
    rn_mean = CalcDoc(
        "rn mean",
        field="rn_mean",
        sources=[NORM_REPORTER],
        view="sid_tdna",
    )
    rn_sd = CalcDoc("rn sd", field="rn_sd", sources=[NORM_REPORTER], view="sid_tdna")
    return [
        CTR,
        NORM_REPORTER,
        quantity,
        amp_score,
        cq_conf,
        rn_mean,
        rn_sd,
    ]


PRESENCE_ABSENCE_NODES: list[Node] = _presence_absence_nodes()


def _primary_analysis_nodes() -> list[Node]:
    ct_mean = CalcDoc("ct mean", field="ct_mean", sources=[CTR], view="sid_tdna")
    ct_sd = CalcDoc("ct sd", field="ct_sd", sources=[CTR], view="sid_tdna")
    ct_se = CalcDoc("ct se", field="ct_se", sources=[CTR], view="sid_tdna")
    return [
        CTR,
        ct_mean,
        ct_sd,
        ct_se,
    ]


PRIMARY_ANALYSIS_NODES: list[Node] = _primary_analysis_nodes()


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
