from collections.abc import Iterator
from functools import cache

from allotropy.calcdocs.appbio_quantstudio.extractor import AppbioQuantstudioExtractor
from allotropy.calcdocs.appbio_quantstudio.views import (
    SampleView as NewSampleView,
    TargetRoleView as NewTargetRoleView,
    TargetView as NewTargetView,
    UuidView,
)
from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.calcdocs.view import ViewData as NewViewData
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    WellItem,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_views import (
    SampleView,
    TargetRoleView,
    TargetView,
)
from allotropy.parsers.appbio_quantstudio.constants import ExperimentType
from allotropy.parsers.appbio_quantstudio.views import ViewData
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none


@cache
def build_amp_score(well_item: WellItem) -> CalculatedDocument | None:
    if (amp_score := well_item.result.amp_score) is None:
        return None

    if well_item.result.cycle_threshold_result is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="amplification score",
        value=amp_score,
        data_sources=[
            DataSource(feature="cycle threshold result", reference=well_item),
        ],
    )


@cache
def build_cq_conf(well_item: WellItem) -> CalculatedDocument | None:
    if (cq_conf := well_item.result.cq_conf) is None:
        return None

    if well_item.result.cycle_threshold_result is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="cq confidence",
        value=cq_conf,
        data_sources=[
            DataSource(feature="cycle threshold result", reference=well_item),
        ],
    )


@cache
def build_quantity(
    view_tr_data: ViewData[WellItem] | None,
    target: str,
    well_item: WellItem,
) -> CalculatedDocument | None:
    if (quantity := well_item.result.quantity) is None:
        return None

    data_sources = []
    if well_item.result.cycle_threshold_result is None:
        return None

    data_sources.append(
        DataSource(feature="cycle threshold result", reference=well_item)
    )

    if view_tr_data:
        if y_intercept_ref := build_y_intercept(view_tr_data, target):
            data_sources.append(
                DataSource(
                    feature="y-intercept",
                    reference=y_intercept_ref,
                )
            )

        if slope_ref := build_slope(view_tr_data, target):
            data_sources.append(
                DataSource(
                    feature="slope",
                    reference=slope_ref,
                )
            )

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="quantity",
        value=quantity,
        data_sources=data_sources,
    )


@cache
def build_quantity_mean(
    view_st_data: ViewData[WellItem],
    view_tr_data: ViewData[WellItem],
    sample: str,
    target: str,
) -> CalculatedDocument | None:
    well_items = view_st_data.get_leaf_item(sample, target)
    if (quantity_mean := well_items[0].result.quantity_mean) is None:
        return None

    data_sources = []
    for well_item in well_items:
        quantity_ref = build_quantity(view_tr_data, target, well_item)
        if quantity_ref is None:
            return None

        data_sources.append(
            DataSource(
                feature="quantity",
                reference=quantity_ref,
            )
        )

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="quantity mean",
        value=quantity_mean,
        data_sources=data_sources,
    )


@cache
def build_quantity_sd(
    view_st_data: ViewData[WellItem],
    view_tr_data: ViewData[WellItem],
    sample: str,
    target: str,
) -> CalculatedDocument | None:
    well_items = view_st_data.get_leaf_item(sample, target)
    if (quantity_sd := well_items[0].result.quantity_sd) is None:
        return None

    data_sources = []
    for well_item in well_items:
        quantity_ref = build_quantity(view_tr_data, target, well_item)
        if quantity_ref is None:
            return None

        data_sources.append(
            DataSource(
                feature="quantity",
                reference=quantity_ref,
            )
        )

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="quantity sd",
        value=quantity_sd,
        data_sources=data_sources,
    )


@cache
def build_ct_mean(
    view_data: ViewData[WellItem], sample: str, target: str
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (ct_mean := well_items[0].result.ct_mean) is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="ct mean",
        value=ct_mean,
        data_sources=[
            DataSource(feature="cycle threshold result", reference=well_item)
            for well_item in well_items
        ],
    )


@cache
def build_ct_sd(
    view_data: ViewData[WellItem], sample: str, target: str
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (ct_sd := well_items[0].result.ct_sd) is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="ct sd",
        value=ct_sd,
        data_sources=[
            DataSource(feature="cycle threshold result", reference=well_item)
            for well_item in well_items
        ],
    )


@cache
def build_delta_ct_mean(
    view_data: ViewData[WellItem],
    sample: str,
    target: str,
    r_target: str,
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (delta_ct_mean := well_items[0].result.delta_ct_mean) is None:
        return None

    ct_mean_ref = build_ct_mean(view_data, sample, target)
    if ct_mean_ref is None:
        return None

    r_ct_mean_ref = build_ct_mean(view_data, sample, r_target)
    if r_ct_mean_ref is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="delta ct mean",
        value=delta_ct_mean,
        data_sources=[
            DataSource(
                feature="ct mean",
                reference=ct_mean_ref,
            ),
            DataSource(
                feature="ct mean",
                reference=r_ct_mean_ref,
            ),
        ],
    )


@cache
def build_delta_ct_se(
    view_data: ViewData[WellItem], sample: str, target: str, r_target: str
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (delta_ct_se := well_items[0].result.delta_ct_se) is None:
        return None

    ct_mean_ref = build_ct_mean(view_data, sample, target)
    if ct_mean_ref is None:
        return None

    r_ct_mean_ref = build_ct_mean(view_data, sample, r_target)
    if r_ct_mean_ref is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="delta ct se",
        value=delta_ct_se,
        data_sources=[
            DataSource(feature="ct mean", reference=ct_mean_ref),
            DataSource(feature="ct mean", reference=r_ct_mean_ref),
        ],
    )


@cache
def build_delta_delta_ct(
    view_data: ViewData[WellItem],
    sample: str,
    target: str,
    r_sample: str,
    r_target: str,
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (delta_delta_ct := well_items[0].result.delta_delta_ct) is None:
        return None

    delta_ct_mean_ref = build_delta_ct_mean(view_data, sample, target, r_target)
    if delta_ct_mean_ref is None:
        return None

    r_delta_ct_mean_ref = build_delta_ct_mean(view_data, r_sample, target, r_target)
    if r_delta_ct_mean_ref is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="delta delta ct",
        value=delta_delta_ct,
        data_sources=[
            DataSource(
                feature="delta ct mean",
                reference=delta_ct_mean_ref,
            ),
            DataSource(
                feature="delta ct mean",
                reference=r_delta_ct_mean_ref,
            ),
        ],
    )


@cache
def build_rq(
    view_data: ViewData[WellItem],
    sample: str,
    target: str,
    r_sample: str,
    r_target: str,
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (rq := well_items[0].result.rq) is None:
        return None

    delta_delta_ct_ref = build_delta_delta_ct(
        view_data, sample, target, r_sample, r_target
    )
    if delta_delta_ct_ref is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="rq",
        value=rq,
        data_sources=[
            DataSource(
                feature="delta delta ct",
                reference=delta_delta_ct_ref,
            )
        ],
    )


@cache
def build_rq_min(
    view_data: ViewData[WellItem],
    sample: str,
    target: str,
    r_sample: str,
    r_target: str,
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (rq_min := well_items[0].result.rq_min) is None:
        return None

    rq_ref = build_rq(view_data, sample, target, r_sample, r_target)
    if rq_ref is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="rq min",
        value=rq_min,
        data_sources=[
            DataSource(
                feature="rq",
                reference=rq_ref,
            )
        ],
    )


@cache
def build_rq_max(
    view_data: ViewData[WellItem],
    sample: str,
    target: str,
    r_sample: str,
    r_target: str,
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (rq_max := well_items[0].result.rq_max) is None:
        return None

    rq_ref = build_rq(view_data, sample, target, r_sample, r_target)
    if rq_ref is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="rq max",
        value=rq_max,
        data_sources=[
            DataSource(
                feature="rq",
                reference=rq_ref,
            ),
        ],
    )


@cache
def build_relative_rq(
    view_st_data: ViewData[WellItem],
    view_tr_data: ViewData[WellItem],
    sample: str,
    target: str,
) -> CalculatedDocument | None:
    well_items = view_st_data.get_leaf_item(sample, target)
    if (rq := well_items[0].result.rq) is None:
        return None

    quantity_mean_ref = build_quantity_mean(view_st_data, view_tr_data, sample, target)
    if quantity_mean_ref is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="rq",
        value=rq,
        data_sources=[
            DataSource(
                feature="quantity mean",
                reference=quantity_mean_ref,
            )
        ],
    )


@cache
def build_relative_rq_min(
    view_st_data: ViewData[WellItem],
    view_tr_data: ViewData[WellItem],
    sample: str,
    target: str,
) -> CalculatedDocument | None:
    well_items = view_st_data.get_leaf_item(sample, target)
    if (rq_min := well_items[0].result.rq_min) is None:
        return None

    relative_rq_ref = build_relative_rq(view_st_data, view_tr_data, sample, target)
    if relative_rq_ref is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="rq min",
        value=rq_min,
        data_sources=[
            DataSource(
                feature="rq",
                reference=relative_rq_ref,
            )
        ],
    )


@cache
def build_relative_rq_max(
    view_st_data: ViewData[WellItem],
    view_tr_data: ViewData[WellItem],
    sample: str,
    target: str,
) -> CalculatedDocument | None:
    well_items = view_st_data.get_leaf_item(sample, target)
    if (rq_max := well_items[0].result.rq_max) is None:
        return None

    relative_rq_ref = build_relative_rq(view_st_data, view_tr_data, sample, target)
    if relative_rq_ref is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="rq max",
        value=rq_max,
        data_sources=[
            DataSource(
                feature="rq",
                reference=relative_rq_ref,
            ),
        ],
    )


@cache
def build_rn_mean(
    view_data: ViewData[WellItem], sample: str, target: str
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (rn_mean := well_items[0].result.rn_mean) is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="rn mean",
        value=rn_mean,
        data_sources=[
            DataSource(feature="normalized reporter result", reference=well_item)
            for well_item in well_items
        ],
    )


@cache
def build_rn_sd(
    view_data: ViewData[WellItem], sample: str, target: str
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(sample, target)
    if (rn_sd := well_items[0].result.rn_sd) is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="rn sd",
        value=rn_sd,
        data_sources=[
            DataSource(feature="normalized reporter result", reference=well_item)
            for well_item in well_items
        ],
    )


@cache
def build_y_intercept(
    view_data: ViewData[WellItem], target: str
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(target)
    if (y_intercept := well_items[0].result.y_intercept) is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="y intercept",
        value=y_intercept,
        data_sources=[
            DataSource(feature="cycle threshold result", reference=well_item)
            for well_item in well_items
        ],
    )


@cache
def build_r_squared(
    view_data: ViewData[WellItem], target: str
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(target)
    if (r_squared := well_items[0].result.r_squared) is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="r^2",
        value=r_squared,
        data_sources=[
            DataSource(feature="cycle threshold result", reference=well_item)
            for well_item in well_items
        ],
    )


@cache
def build_slope(
    view_data: ViewData[WellItem], target: str
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(target)
    if (slope := well_items[0].result.slope) is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="slope",
        value=slope,
        data_sources=[
            DataSource(feature="cycle threshold result", reference=well_item)
            for well_item in well_items
        ],
    )


@cache
def build_efficiency(
    view_data: ViewData[WellItem], target: str
) -> CalculatedDocument | None:
    well_items = view_data.get_leaf_item(target)
    if (efficiency := well_items[0].result.efficiency) is None:
        return None

    return CalculatedDocument(
        uuid=random_uuid_str(),
        name="efficiency",
        value=efficiency,
        data_sources=[
            DataSource(feature="cycle threshold result", reference=well_item)
            for well_item in well_items
        ],
    )


def ctr() -> MeasurementConfig:
    return MeasurementConfig(
        name="cycle threshold result",
        value="cycle_threshold_result",
    )


def norm_reporter_result() -> MeasurementConfig:
    return MeasurementConfig(
        name="normalized reporter result",
        value="normalized_reporter_result",
    )


def amplification_score(view_data: NewViewData) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="amplification score",
        value="amp_score",
        view_data=view_data,
        source_configs=(ctr(),),
    )


def cq_confidence(view_data: NewViewData) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="cq confidence",
        value="cq_conf",
        view_data=view_data,
        source_configs=(ctr(),),
    )


def y_intercept(view_data: NewViewData) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="y intercept",
        value="y_intercept",
        view_data=view_data,
        source_configs=(ctr(),),
    )


def slope(view_data: NewViewData) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="slope",
        value="slope",
        view_data=view_data,
        source_configs=(ctr(),),
    )


def ct_mean(view_data: NewViewData) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="ct mean",
        value="ct_mean",
        view_data=view_data,
        source_configs=(ctr(),),
    )


def ct_sd(view_data: NewViewData) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="ct sd",
        value="ct_sd",
        view_data=view_data,
        source_configs=(ctr(),),
    )


def rn_mean(view_data: NewViewData) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="rn mean",
        value="rn_mean",
        view_data=view_data,
        source_configs=(norm_reporter_result(),),
    )


def rn_sd(view_data: NewViewData) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="rn sd",
        value="rn_sd",
        view_data=view_data,
        source_configs=(norm_reporter_result(),),
    )


def quantity(
    view_data: NewViewData,
    y_intercept_conf: CalculatedDataConfig | None = None,
    slope_conf: CalculatedDataConfig | None = None,
) -> CalculatedDataConfig:
    ctr_conf = ctr()
    return CalculatedDataConfig(
        name="quantity",
        value="quantity",
        view_data=view_data,
        source_configs=tuple(
            config for config in [ctr_conf, y_intercept_conf, slope_conf] if config
        ),
    )


def quantity_mean(
    view_data: NewViewData,
    quantity_conf: CalculatedDataConfig,
) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="quantity mean",
        value="quantity_mean",
        view_data=view_data,
        source_configs=(quantity_conf,),
    )


def quantity_sd(
    view_data: NewViewData,
    quantity_conf: CalculatedDataConfig,
) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="quantity sd",
        value="quantity_sd",
        view_data=view_data,
        source_configs=(quantity_conf,),
    )


def delta_ct_se(
    view_data: NewViewData,
    ct_sd_conf: CalculatedDataConfig,
    ref_ct_sd_conf: CalculatedDataConfig,
) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="delta ct se",
        value="delta_ct_se",
        view_data=view_data,
        source_configs=(ct_sd_conf, ref_ct_sd_conf),
    )


def delta_ct_mean(
    view_data: NewViewData,
    adj_eq_ct_mean_conf: CalculatedDataConfig,
    ref_adj_eq_ct_mean_conf: CalculatedDataConfig,
) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="delta ct mean",
        value="delta_ct_mean",
        view_data=view_data,
        source_configs=(adj_eq_ct_mean_conf, ref_adj_eq_ct_mean_conf),
    )


def delta_delta_ct(
    view_data: NewViewData,
    delta_ct_conf: CalculatedDataConfig,
    ref_delta_ct_conf: CalculatedDataConfig,
) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="delta delta ct",
        value="delta_delta_ct",
        view_data=view_data,
        source_configs=(delta_ct_conf, ref_delta_ct_conf),
    )


def rq(
    view_data: NewViewData,
    delta_delta_ct_conf: CalculatedDataConfig,
) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="rq",
        value="rq",
        view_data=view_data,
        source_configs=(delta_delta_ct_conf,),
    )


def rq_min(
    view_data: NewViewData,
    rq_conf: CalculatedDataConfig,
) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="rq min",
        value="rq_min",
        view_data=view_data,
        source_configs=(rq_conf,),
    )


def rq_max(
    view_data: NewViewData,
    rq_conf: CalculatedDataConfig,
) -> CalculatedDataConfig:
    return CalculatedDataConfig(
        name="rq max",
        value="rq_max",
        view_data=view_data,
        source_configs=(rq_conf,),
    )


def yield_documents(
    calc_docs: list[CalculatedDocument | None],
) -> Iterator[CalculatedDocument]:
    for calc_doc in calc_docs:
        if calc_doc:
            yield from calc_doc.iter_struct()


def iter_comparative_ct_calc_docs(
    well_items: list[WellItem],
    r_sample: str,
    r_target: str,
) -> Iterator[CalculatedDocument]:
    # Y-intercept, Slope, Quantity, Amplification score, Cq confidence
    # Quantity Mean, Quantity SD, Ct Mean, Ct SD
    # Delta Ct SE, Delta Ct Mean,
    # Delta Delta Ct, RQ, RQ min, RQ max
    elements = AppbioQuantstudioExtractor.get_elements(well_items)

    sid_tdna_view_data = NewSampleView(sub_view=NewTargetView()).apply(elements)
    sid_ref_tdna_view_data = NewSampleView(
        reference=r_sample, sub_view=NewTargetView()
    ).apply(elements)
    sid_tdna_ref_view_data = NewSampleView(
        sub_view=NewTargetView(is_reference=True, reference=r_target)
    ).apply(elements)
    sid_tdna_blacklist_view_data = NewSampleView(
        sub_view=NewTargetView(blacklist=[r_target] if r_target is not None else None)
    ).apply(elements)
    sid_tdna_uuid_view_data = NewSampleView(
        sub_view=NewTargetView(sub_view=UuidView())
    ).apply(elements)
    tdna_view_data = NewTargetRoleView().apply(elements)

    quantity_conf = quantity(
        sid_tdna_uuid_view_data,
        y_intercept(tdna_view_data),
        slope(tdna_view_data),
    )

    configs = CalcDocsConfig(
        [
            quantity_conf,
            amplification_score(sid_tdna_uuid_view_data),
            cq_confidence(sid_tdna_uuid_view_data),
            quantity_mean(sid_tdna_view_data, quantity_conf),
            quantity_sd(sid_tdna_view_data, quantity_conf),
            ct_mean(sid_tdna_view_data),
            ct_sd(sid_tdna_view_data),
            delta_ct_se(
                sid_tdna_view_data,
                ct_mean(sid_tdna_view_data),
                ct_mean(sid_tdna_ref_view_data),
            ),
            rq_min(
                sid_tdna_blacklist_view_data,
                rq(
                    sid_tdna_view_data,
                    delta_delta_ct(
                        sid_tdna_view_data,
                        delta_ct_mean(
                            sid_tdna_view_data,
                            ct_mean(sid_tdna_view_data),
                            ct_mean(sid_tdna_ref_view_data),
                        ),
                        delta_ct_mean(
                            sid_ref_tdna_view_data,
                            ct_mean(sid_tdna_view_data),
                            ct_mean(sid_tdna_ref_view_data),
                        ),
                    ),
                ),
            ),
            rq_max(
                sid_tdna_blacklist_view_data,
                rq(
                    sid_tdna_view_data,
                    delta_delta_ct(
                        sid_tdna_view_data,
                        delta_ct_mean(
                            sid_tdna_view_data,
                            ct_mean(sid_tdna_view_data),
                            ct_mean(sid_tdna_ref_view_data),
                        ),
                        delta_ct_mean(
                            sid_ref_tdna_view_data,
                            ct_mean(sid_tdna_view_data),
                            ct_mean(sid_tdna_ref_view_data),
                        ),
                    ),
                ),
            ),
        ]
    )

    for calc_doc in configs.construct():
        yield from calc_doc.iter_struct()


def iter_standard_curve_calc_docs(
    view_st_data: ViewData[WellItem],
    view_tr_data: ViewData[WellItem],
) -> Iterator[CalculatedDocument]:
    # Quantity, Quantity Mean, Quantity SD, Ct Mean, Ct SD, Y-Intercept,
    # R(superscript 2), Slope, Efficiency, Amplification score, Cq confidence
    calc_docs: list[CalculatedDocument | None] = []
    for sample, target in view_st_data.iter_keys():
        for well_item in view_st_data.get_leaf_item(sample, target):
            calc_docs.append(build_quantity(view_tr_data, target, well_item))
            calc_docs.append(build_amp_score(well_item))
            calc_docs.append(build_cq_conf(well_item))

        calc_docs.append(
            build_quantity_mean(view_st_data, view_tr_data, sample, target)
        )
        calc_docs.append(build_quantity_sd(view_st_data, view_tr_data, sample, target))
        calc_docs.append(build_ct_mean(view_st_data, sample, target))
        calc_docs.append(build_ct_sd(view_st_data, sample, target))

    for target in view_tr_data.data:
        calc_docs.append(build_y_intercept(view_tr_data, target))
        calc_docs.append(build_r_squared(view_tr_data, target))
        calc_docs.append(build_slope(view_tr_data, target))
        calc_docs.append(build_efficiency(view_tr_data, target))

    yield from yield_documents(calc_docs)


def iter_relative_standard_curve_calc_docs(
    view_st_data: ViewData[WellItem],
    view_tr_data: ViewData[WellItem],
) -> Iterator[CalculatedDocument]:
    # Quantity, Quantity Mean, Quantity SD, Ct Mean, Ct SD, RQ, RQ min,
    # RQ max, Y-Intercept, R(superscript 2), Slope, Efficiency,
    # Amplification score, Cq confidence
    calc_docs: list[CalculatedDocument | None] = []
    for sample, target in view_st_data.iter_keys():
        for well_item in view_st_data.get_leaf_item(sample, target):
            calc_docs.append(build_quantity(view_tr_data, target, well_item))
            calc_docs.append(build_amp_score(well_item))
            calc_docs.append(build_cq_conf(well_item))

        calc_docs.append(
            build_quantity_mean(view_st_data, view_tr_data, sample, target)
        )
        calc_docs.append(build_quantity_sd(view_st_data, view_tr_data, sample, target))
        calc_docs.append(build_ct_mean(view_st_data, sample, target))
        calc_docs.append(build_ct_sd(view_st_data, sample, target))
        calc_docs.append(
            build_relative_rq_min(view_st_data, view_tr_data, sample, target)
        )
        calc_docs.append(
            build_relative_rq_max(view_st_data, view_tr_data, sample, target)
        )

    for target in view_tr_data.data:
        calc_docs.append(build_y_intercept(view_tr_data, target))
        calc_docs.append(build_r_squared(view_tr_data, target))
        calc_docs.append(build_slope(view_tr_data, target))
        calc_docs.append(build_efficiency(view_tr_data, target))

    yield from yield_documents(calc_docs)


def iter_presence_absence_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    # Quantity, Amp score, Cq confidence, Rn Mean, Rn SD
    elements = AppbioQuantstudioExtractor.get_elements(well_items)

    sid_tdna_view_data = NewSampleView(sub_view=NewTargetView()).apply(elements)
    sid_tdna_uuid_view_data = NewSampleView(
        sub_view=NewTargetView(sub_view=UuidView())
    ).apply(elements)

    configs = CalcDocsConfig(
        [
            quantity(sid_tdna_uuid_view_data),
            amplification_score(sid_tdna_uuid_view_data),
            cq_confidence(sid_tdna_uuid_view_data),
            rn_mean(sid_tdna_view_data),
            rn_sd(sid_tdna_view_data),
        ]
    )

    for calc_doc in configs.construct():
        yield from calc_doc.iter_struct()


def iter_calculated_data_documents(
    well_items: list[WellItem],
    experiment_type: ExperimentType,
    r_sample: str | None,
    r_target: str | None,
) -> Iterator[CalculatedDocument]:
    well_items = [well_item for well_item in well_items if well_item.has_result]
    view_st = SampleView(sub_view=TargetView())
    view_st_data = view_st.apply(well_items)

    view_tr = TargetRoleView()
    view_tr_data = view_tr.apply(well_items)

    if experiment_type == ExperimentType.relative_standard_curve_qpcr_experiment:
        yield from iter_relative_standard_curve_calc_docs(
            view_st_data,
            view_tr_data,
        )
    elif experiment_type == ExperimentType.comparative_ct_qpcr_experiment:
        yield from iter_comparative_ct_calc_docs(
            well_items,
            assert_not_none(r_sample),
            assert_not_none(r_target),
        )
    elif experiment_type == ExperimentType.standard_curve_qpcr_experiment:
        yield from iter_standard_curve_calc_docs(
            view_st_data,
            view_tr_data,
        )
    elif experiment_type == ExperimentType.presence_absence_qpcr_experiment:
        yield from iter_presence_absence_calc_docs(well_items)
