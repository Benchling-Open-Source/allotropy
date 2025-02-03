from collections.abc import Iterator

from allotropy.calcdocs.appbio_quantstudio_designandanalysis.config import (
    CalculatedDataConfigWithOptional,
)
from allotropy.calcdocs.appbio_quantstudio_designandanalysis.extractor import (
    AppbioQuantstudioDAExtractor,
)
from allotropy.calcdocs.appbio_quantstudio_designandanalysis.views import (
    SampleView,
    TargetRoleView,
    TargetView,
    UuidView,
)
from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    WellItem,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)


def iter_standard_curve_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    # Quantity, Quantity Mean, Quantity SD, Ct Mean, Ct SD, Y-Intercept,
    # R(superscript 2), Slope, Efficiency, Amp score, Cq confidence
    elements = AppbioQuantstudioDAExtractor.get_elements(well_items)

    sid_tdna_view_data = SampleView(sub_view=TargetView()).apply(elements)
    sid_tdna_uuid_view_data = SampleView(
        sub_view=TargetView(sub_view=UuidView())
    ).apply(elements)
    tdna_view_data = TargetRoleView().apply(elements)

    configs = CalcDocsConfig(
        [
            CalculatedDataConfig(
                name="quantity",
                value="quantity",
                view_data=sid_tdna_uuid_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                    CalculatedDataConfig(
                        name="y intercept",
                        value="y_intercept",
                        view_data=tdna_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                        ),
                    ),
                    CalculatedDataConfig(
                        name="slope",
                        value="slope",
                        view_data=tdna_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                        ),
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="amplification score",
                value="amp_score",
                view_data=sid_tdna_uuid_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="cq confidence",
                value="cq_conf",
                view_data=sid_tdna_uuid_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="quantity mean",
                value="quantity_mean",
                view_data=sid_tdna_view_data,
                source_configs=(
                    CalculatedDataConfig(
                        name="quantity",
                        value="quantity",
                        view_data=sid_tdna_uuid_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                            CalculatedDataConfig(
                                name="y intercept",
                                value="y_intercept",
                                view_data=tdna_view_data,
                                source_configs=(
                                    MeasurementConfig(
                                        name="cycle threshold result",
                                        value="cycle_threshold_result",
                                    ),
                                ),
                            ),
                            CalculatedDataConfig(
                                name="slope",
                                value="slope",
                                view_data=tdna_view_data,
                                source_configs=(
                                    MeasurementConfig(
                                        name="cycle threshold result",
                                        value="cycle_threshold_result",
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="quantity sd",
                value="quantity_sd",
                view_data=sid_tdna_view_data,
                source_configs=(
                    CalculatedDataConfig(
                        name="quantity",
                        value="quantity",
                        view_data=sid_tdna_uuid_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                            CalculatedDataConfig(
                                name="y intercept",
                                value="y_intercept",
                                view_data=tdna_view_data,
                                source_configs=(
                                    MeasurementConfig(
                                        name="cycle threshold result",
                                        value="cycle_threshold_result",
                                    ),
                                ),
                            ),
                            CalculatedDataConfig(
                                name="slope",
                                value="slope",
                                view_data=tdna_view_data,
                                source_configs=(
                                    MeasurementConfig(
                                        name="cycle threshold result",
                                        value="cycle_threshold_result",
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="ct mean",
                value="ct_mean",
                view_data=sid_tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="ct sd",
                value="ct_sd",
                view_data=sid_tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="y intercept",
                value="y_intercept",
                view_data=tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="r^2",
                value="r_squared",
                view_data=tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="slope",
                value="slope",
                view_data=tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="efficiency",
                value="efficiency",
                view_data=tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
        ]
    )

    for calc_doc in configs.construct():
        yield from calc_doc.iter_struct()


def iter_relative_standard_curve_calc_docs(
    well_items: list[WellItem],
    r_sample: str,
    r_target: str | None,
) -> Iterator[CalculatedDocument]:
    # Quantity, Quantity Mean, Quantity SD, Ct Mean, Ct SD, RQ, RQ min,
    # RQ max, Y-Intercept, R(superscript 2), Slope, Efficiency,
    # Amp score, Cq confidence
    elements = AppbioQuantstudioDAExtractor.get_elements(well_items)

    sid_tdna_view_data = SampleView(sub_view=TargetView()).apply(elements)
    sid_ref_tdna_view_data = SampleView(
        reference=r_sample, sub_view=TargetView()
    ).apply(elements)
    sid_tdna_ref_view_data = SampleView(
        sub_view=TargetView(is_reference=True, reference=r_target)
    ).apply(elements)
    sid_tdna_blacklist_view_data = SampleView(
        sub_view=TargetView(blacklist=[r_target] if r_target is not None else None)
    ).apply(elements)
    sid_tdna_uuid_view_data = SampleView(
        sub_view=TargetView(sub_view=UuidView())
    ).apply(elements)
    tdna_view_data = TargetRoleView().apply(elements)

    configs = CalcDocsConfig(
        [
            CalculatedDataConfig(
                name="quantity",
                value="quantity",
                view_data=sid_tdna_uuid_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                    CalculatedDataConfig(
                        name="y intercept",
                        value="y_intercept",
                        view_data=tdna_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                        ),
                    ),
                    CalculatedDataConfig(
                        name="slope",
                        value="slope",
                        view_data=tdna_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                        ),
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="amplification score",
                value="amp_score",
                view_data=sid_tdna_uuid_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="cq confidence",
                value="cq_conf",
                view_data=sid_tdna_uuid_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="ct mean",
                value="ct_mean",
                view_data=sid_tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="ct sd",
                value="ct_sd",
                view_data=sid_tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="delta equivalent ct sd",
                value="delta_ct_sd",
                view_data=sid_tdna_view_data,
                source_configs=(
                    CalculatedDataConfig(
                        name="ct sd",
                        value="ct_sd",
                        view_data=sid_tdna_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                        ),
                    ),
                    CalculatedDataConfig(
                        name="ct sd",
                        value="ct_sd",
                        view_data=sid_tdna_ref_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                        ),
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="delta equivalent ct se",
                value="delta_ct_se",
                view_data=sid_tdna_view_data,
                source_configs=(
                    CalculatedDataConfig(
                        name="ct se",
                        value="ct_se",
                        view_data=sid_tdna_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                        ),
                    ),
                    CalculatedDataConfig(
                        name="ct se",
                        value="ct_se",
                        view_data=sid_tdna_ref_view_data,
                        source_configs=(
                            MeasurementConfig(
                                name="cycle threshold result",
                                value="cycle_threshold_result",
                            ),
                        ),
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="relative rq min",
                value="rq_min",
                view_data=sid_tdna_view_data,
                source_configs=(
                    CalculatedDataConfig(
                        name="relative rq",
                        value="rq",
                        view_data=sid_tdna_view_data,
                        source_configs=(
                            CalculatedDataConfig(
                                name="quantity mean",
                                value="quantity_mean",
                                view_data=sid_tdna_view_data,
                                source_configs=(
                                    CalculatedDataConfig(
                                        name="quantity",
                                        value="quantity",
                                        view_data=sid_tdna_uuid_view_data,
                                        source_configs=(
                                            MeasurementConfig(
                                                name="cycle threshold result",
                                                value="cycle_threshold_result",
                                            ),
                                            CalculatedDataConfig(
                                                name="y intercept",
                                                value="y_intercept",
                                                view_data=tdna_view_data,
                                                source_configs=(
                                                    MeasurementConfig(
                                                        name="cycle threshold result",
                                                        value="cycle_threshold_result",
                                                    ),
                                                ),
                                            ),
                                            CalculatedDataConfig(
                                                name="slope",
                                                value="slope",
                                                view_data=tdna_view_data,
                                                source_configs=(
                                                    MeasurementConfig(
                                                        name="cycle threshold result",
                                                        value="cycle_threshold_result",
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="relative rq max",
                value="rq_max",
                view_data=sid_tdna_view_data,
                source_configs=(
                    CalculatedDataConfig(
                        name="relative rq",
                        value="rq",
                        view_data=sid_tdna_view_data,
                        source_configs=(
                            CalculatedDataConfig(
                                name="quantity mean",
                                value="quantity_mean",
                                view_data=sid_tdna_view_data,
                                source_configs=(
                                    CalculatedDataConfig(
                                        name="quantity",
                                        value="quantity",
                                        view_data=sid_tdna_uuid_view_data,
                                        source_configs=(
                                            MeasurementConfig(
                                                name="cycle threshold result",
                                                value="cycle_threshold_result",
                                            ),
                                            CalculatedDataConfig(
                                                name="y intercept",
                                                value="y_intercept",
                                                view_data=tdna_view_data,
                                                source_configs=(
                                                    MeasurementConfig(
                                                        name="cycle threshold result",
                                                        value="cycle_threshold_result",
                                                    ),
                                                ),
                                            ),
                                            CalculatedDataConfig(
                                                name="slope",
                                                value="slope",
                                                view_data=tdna_view_data,
                                                source_configs=(
                                                    MeasurementConfig(
                                                        name="cycle threshold result",
                                                        value="cycle_threshold_result",
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="rq min",
                value="rq_min",
                view_data=sid_tdna_blacklist_view_data,
                source_configs=(
                    CalculatedDataConfig(
                        name="rq",
                        value="rq",
                        view_data=sid_tdna_view_data,
                        source_configs=(
                            CalculatedDataConfig(
                                name="delta delta equivalent ct",
                                value="delta_delta_ct",
                                view_data=sid_tdna_view_data,
                                source_configs=(
                                    CalculatedDataConfig(
                                        name="delta equivalent ct mean",
                                        value="delta_ct_mean",
                                        view_data=sid_tdna_view_data,
                                        source_configs=(
                                            CalculatedDataConfigWithOptional(
                                                name="adjusted equivalent ct mean",
                                                value="adj_eq_ct_mean",
                                                view_data=sid_tdna_view_data,
                                                optional=True,
                                                source_configs=(
                                                    CalculatedDataConfig(
                                                        name="equivalent ct mean",
                                                        value="eq_ct_mean",
                                                        view_data=sid_tdna_view_data,
                                                        source_configs=(
                                                            CalculatedDataConfig(
                                                                name="ct mean",
                                                                value="ct_mean",
                                                                view_data=sid_tdna_view_data,
                                                                source_configs=(
                                                                    MeasurementConfig(
                                                                        name="cycle threshold result",
                                                                        value="cycle_threshold_result",
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                            CalculatedDataConfigWithOptional(
                                                name="adjusted equivalent ct mean",
                                                value="adj_eq_ct_mean",
                                                view_data=sid_tdna_ref_view_data,
                                                optional=True,
                                                source_configs=(
                                                    CalculatedDataConfig(
                                                        name="equivalent ct mean",
                                                        value="eq_ct_mean",
                                                        view_data=sid_tdna_view_data,
                                                        source_configs=(
                                                            CalculatedDataConfig(
                                                                name="ct mean",
                                                                value="ct_mean",
                                                                view_data=sid_tdna_view_data,
                                                                source_configs=(
                                                                    MeasurementConfig(
                                                                        name="cycle threshold result",
                                                                        value="cycle_threshold_result",
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                    CalculatedDataConfig(
                                        name="delta equivalent ct mean",
                                        value="delta_ct_mean",
                                        view_data=sid_ref_tdna_view_data,
                                        source_configs=(
                                            CalculatedDataConfigWithOptional(
                                                name="adjusted equivalent ct mean",
                                                value="adj_eq_ct_mean",
                                                view_data=sid_tdna_view_data,
                                                optional=True,
                                                source_configs=(
                                                    CalculatedDataConfig(
                                                        name="equivalent ct mean",
                                                        value="eq_ct_mean",
                                                        view_data=sid_tdna_view_data,
                                                        source_configs=(
                                                            CalculatedDataConfig(
                                                                name="ct mean",
                                                                value="ct_mean",
                                                                view_data=sid_tdna_view_data,
                                                                source_configs=(
                                                                    MeasurementConfig(
                                                                        name="cycle threshold result",
                                                                        value="cycle_threshold_result",
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                            CalculatedDataConfigWithOptional(
                                                name="adjusted equivalent ct mean",
                                                value="adj_eq_ct_mean",
                                                view_data=sid_tdna_ref_view_data,
                                                optional=True,
                                                source_configs=(
                                                    CalculatedDataConfig(
                                                        name="equivalent ct mean",
                                                        value="eq_ct_mean",
                                                        view_data=sid_tdna_view_data,
                                                        source_configs=(
                                                            CalculatedDataConfig(
                                                                name="ct mean",
                                                                value="ct_mean",
                                                                view_data=sid_tdna_view_data,
                                                                source_configs=(
                                                                    MeasurementConfig(
                                                                        name="cycle threshold result",
                                                                        value="cycle_threshold_result",
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="rq max",
                value="rq_max",
                view_data=sid_tdna_blacklist_view_data,
                source_configs=(
                    CalculatedDataConfig(
                        name="rq",
                        value="rq",
                        view_data=sid_tdna_view_data,
                        source_configs=(
                            CalculatedDataConfig(
                                name="delta delta equivalent ct",
                                value="delta_delta_ct",
                                view_data=sid_tdna_view_data,
                                source_configs=(
                                    CalculatedDataConfig(
                                        name="delta equivalent ct mean",
                                        value="delta_ct_mean",
                                        view_data=sid_tdna_view_data,
                                        source_configs=(
                                            CalculatedDataConfigWithOptional(
                                                name="adjusted equivalent ct mean",
                                                value="adj_eq_ct_mean",
                                                view_data=sid_tdna_view_data,
                                                optional=True,
                                                source_configs=(
                                                    CalculatedDataConfig(
                                                        name="equivalent ct mean",
                                                        value="eq_ct_mean",
                                                        view_data=sid_tdna_view_data,
                                                        source_configs=(
                                                            CalculatedDataConfig(
                                                                name="ct mean",
                                                                value="ct_mean",
                                                                view_data=sid_tdna_view_data,
                                                                source_configs=(
                                                                    MeasurementConfig(
                                                                        name="cycle threshold result",
                                                                        value="cycle_threshold_result",
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                            CalculatedDataConfigWithOptional(
                                                name="adjusted equivalent ct mean",
                                                value="adj_eq_ct_mean",
                                                view_data=sid_tdna_ref_view_data,
                                                optional=True,
                                                source_configs=(
                                                    CalculatedDataConfig(
                                                        name="equivalent ct mean",
                                                        value="eq_ct_mean",
                                                        view_data=sid_tdna_view_data,
                                                        source_configs=(
                                                            CalculatedDataConfig(
                                                                name="ct mean",
                                                                value="ct_mean",
                                                                view_data=sid_tdna_view_data,
                                                                source_configs=(
                                                                    MeasurementConfig(
                                                                        name="cycle threshold result",
                                                                        value="cycle_threshold_result",
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                    CalculatedDataConfig(
                                        name="delta equivalent ct mean",
                                        value="delta_ct_mean",
                                        view_data=sid_ref_tdna_view_data,
                                        source_configs=(
                                            CalculatedDataConfigWithOptional(
                                                name="adjusted equivalent ct mean",
                                                value="adj_eq_ct_mean",
                                                view_data=sid_tdna_view_data,
                                                optional=True,
                                                source_configs=(
                                                    CalculatedDataConfig(
                                                        name="equivalent ct mean",
                                                        value="eq_ct_mean",
                                                        view_data=sid_tdna_view_data,
                                                        source_configs=(
                                                            CalculatedDataConfig(
                                                                name="ct mean",
                                                                value="ct_mean",
                                                                view_data=sid_tdna_view_data,
                                                                source_configs=(
                                                                    MeasurementConfig(
                                                                        name="cycle threshold result",
                                                                        value="cycle_threshold_result",
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                            CalculatedDataConfigWithOptional(
                                                name="adjusted equivalent ct mean",
                                                value="adj_eq_ct_mean",
                                                view_data=sid_tdna_ref_view_data,
                                                optional=True,
                                                source_configs=(
                                                    CalculatedDataConfig(
                                                        name="equivalent ct mean",
                                                        value="eq_ct_mean",
                                                        view_data=sid_tdna_view_data,
                                                        source_configs=(
                                                            CalculatedDataConfig(
                                                                name="ct mean",
                                                                value="ct_mean",
                                                                view_data=sid_tdna_view_data,
                                                                source_configs=(
                                                                    MeasurementConfig(
                                                                        name="cycle threshold result",
                                                                        value="cycle_threshold_result",
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ]
    )

    for calc_doc in configs.construct():
        yield from calc_doc.iter_struct()


def iter_presence_absence_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    # Rn Mean, Rn SD, Amp score, Cq confidence
    elements = AppbioQuantstudioDAExtractor.get_elements(well_items)

    sid_tdna_view_data = SampleView(sub_view=TargetView()).apply(elements)
    sid_tdna_uuid_view_data = SampleView(
        sub_view=TargetView(sub_view=UuidView())
    ).apply(elements)

    configs = CalcDocsConfig(
        [
            CalculatedDataConfig(
                name="quantity",
                value="quantity",
                view_data=sid_tdna_uuid_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="amplification score",
                value="amp_score",
                view_data=sid_tdna_uuid_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="cq confidence",
                value="cq_conf",
                view_data=sid_tdna_uuid_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="rn mean",
                value="rn_mean",
                view_data=sid_tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="normalized reporter result",
                        value="normalized_reporter_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="rn sd",
                value="rn_sd",
                view_data=sid_tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="normalized reporter result",
                        value="normalized_reporter_result",
                    ),
                ),
            ),
        ]
    )

    for calc_doc in configs.construct():
        yield from calc_doc.iter_struct()


def iter_primary_analysis_calc_docs(
    well_items: list[WellItem],
) -> Iterator[CalculatedDocument]:
    # Ct Mean, Ct SD, Ct SE
    elements = AppbioQuantstudioDAExtractor.get_elements(well_items)

    sid_tdna_view_data = SampleView(sub_view=TargetView()).apply(elements)

    configs = CalcDocsConfig(
        [
            CalculatedDataConfig(
                name="ct mean",
                value="ct_mean",
                view_data=sid_tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="ct sd",
                value="ct_sd",
                view_data=sid_tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
            CalculatedDataConfig(
                name="ct se",
                value="ct_se",
                view_data=sid_tdna_view_data,
                source_configs=(
                    MeasurementConfig(
                        name="cycle threshold result",
                        value="cycle_threshold_result",
                    ),
                ),
            ),
        ]
    )

    for calc_doc in configs.construct():
        yield from calc_doc.iter_struct()
