from collections.abc import Iterator
from typing import Optional
from uuid import uuid4

from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import ExperimentType
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    WellItem,
    WellList,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_views import (
    SampleView,
    TargetRoleView,
    TargetView,
)
from allotropy.parsers.appbio_quantstudio.calculated_document import (
    CalculatedDocument,
    DataSource,
)
from allotropy.parsers.appbio_quantstudio.decorators import cache


class CalculatedDocumentBuilder:
    def __init__(
        self,
        wells: WellList,
        experiment_type: ExperimentType,
        r_target: str,
        r_sample: str,
    ):
        self.experiment_type = experiment_type

        self.r_target = r_target
        self.r_sample = r_sample

        view_st = SampleView(sub_view=TargetView())
        self.view_st_data = view_st.apply(wells.iter_well_items())  # type: ignore[arg-type]

        view_tr = TargetRoleView()
        self.view_tr_data = view_tr.apply(wells.iter_well_items())  # type: ignore[arg-type]

    @staticmethod
    @cache
    def build_quantity(well_item: WellItem) -> Optional[CalculatedDocument]:
        if (quantity := well_item.result.quantity) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="quantity",
            value=quantity,
            data_sources=[
                DataSource(feature="cycle threshold result", reference=well_item),
            ],
        )

    def build_quantity_mean(
        self, sample: str, target: str
    ) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (quantity_mean := well_items[0].result.quantity_mean) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="quantity mean",
            value=quantity_mean,
            data_sources=[
                DataSource(
                    feature="quantity",
                    reference=CalculatedDocumentBuilder.build_quantity(well_item),
                )
                for well_item in well_items
            ],
        )

    def build_quantity_sd(
        self, sample: str, target: str
    ) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (quantity_sd := well_items[0].result.quantity_sd) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="quantity sd",
            value=quantity_sd,
            data_sources=[
                DataSource(
                    feature="quantity",
                    reference=CalculatedDocumentBuilder.build_quantity(well_item),
                )
                for well_item in well_items
            ],
        )

    @cache
    def build_ct_mean(self, sample: str, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (ct_mean := well_items[0].result.ct_mean) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="ct mean",
            value=ct_mean,
            data_sources=[
                DataSource(feature="cycle threshold result", reference=well_item)
                for well_item in well_items
            ],
        )

    def build_ct_sd(self, sample: str, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (ct_sd := well_items[0].result.ct_sd) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="ct sd",
            value=ct_sd,
            data_sources=[
                DataSource(feature="cycle threshold result", reference=well_item)
                for well_item in well_items
            ],
        )

    def build_delta_ct_mean(
        self, sample: str, target: str
    ) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (delta_ct_mean := well_items[0].result.delta_ct_mean) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="delta ct mean",
            value=delta_ct_mean,
            data_sources=[
                DataSource(
                    feature="ct mean",
                    reference=self.build_ct_mean(sample, target),
                ),
                DataSource(
                    feature="ct mean",
                    reference=self.build_ct_mean(sample, self.r_target),
                ),
            ],
        )

    def build_delta_ct_se(
        self, sample: str, target: str
    ) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (delta_ct_se := well_items[0].result.delta_ct_se) is None:
            return None

        source = [
            DataSource(feature="ct mean", reference=well_item)
            for well_item in well_items
        ]

        r_target_source = [
            DataSource(feature="ct mean", reference=well_item)
            for well_item in self.view_st_data.get_leaf_item(sample, self.r_target)
        ]

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="delta ct se",
            value=delta_ct_se,
            data_sources=source + r_target_source,
        )

    def build_delta_delta_ct(
        self, sample: str, target: str
    ) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (delta_delta_ct := well_items[0].result.delta_delta_ct) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="delta delta ct",
            value=delta_delta_ct,
            data_sources=[
                DataSource(
                    feature="delta ct mean",
                    reference=self.build_delta_ct_mean(sample, target),
                ),
                DataSource(
                    feature="delta ct mean",
                    reference=self.build_delta_ct_mean(self.r_sample, target),
                ),
            ],
        )

    @cache
    def build_rq(self, sample: str, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (rq := well_items[0].result.rq) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="rq",
            value=rq,
            data_sources=[
                DataSource(
                    feature="delta delta ct",
                    reference=self.build_delta_delta_ct(sample, target),
                )
            ],
        )

    def build_rq_min(self, sample: str, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (rq_min := well_items[0].result.rq_min) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="rq min",
            value=rq_min,
            data_sources=[
                DataSource(
                    feature="rq",
                    reference=self.build_rq(sample, target),
                )
            ],
        )

    def build_rq_max(self, sample: str, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (rq_max := well_items[0].result.rq_max) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="rq max",
            value=rq_max,
            data_sources=[
                DataSource(feature="rq", reference=self.build_rq(sample, target)),
            ],
        )

    def build_rn_mean(self, sample: str, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (rn_mean := well_items[0].result.rn_mean) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="rn mean",
            value=rn_mean,
            data_sources=[
                DataSource(feature="normalized reporter result", reference=well_item)
                for well_item in well_items
            ],
        )

    def build_rn_sd(self, sample: str, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_st_data.get_leaf_item(sample, target)
        if (rn_sd := well_items[0].result.rn_sd) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="rn sd",
            value=rn_sd,
            data_sources=[
                DataSource(feature="normalized reporter result", reference=well_item)
                for well_item in well_items
            ],
        )

    def build_y_intercept(self, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_tr_data.get_leaf_item(target)
        if (y_intercept := well_items[0].result.y_intercept) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="y intercept",
            value=y_intercept,
            data_sources=[
                DataSource(feature="cycle threshold result", reference=well_item)
                for well_item in well_items
            ],
        )

    def build_r_squared(self, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_tr_data.get_leaf_item(target)
        if (r_squared := well_items[0].result.r_squared) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="r^2",
            value=r_squared,
            data_sources=[
                DataSource(feature="cycle threshold result", reference=well_item)
                for well_item in well_items
            ],
        )

    def build_slope(self, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_tr_data.get_leaf_item(target)
        if (slope := well_items[0].result.slope) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="slope",
            value=slope,
            data_sources=[
                DataSource(feature="cycle threshold result", reference=well_item)
                for well_item in well_items
            ],
        )

    def build_efficiency(self, target: str) -> Optional[CalculatedDocument]:
        well_items = self.view_tr_data.get_leaf_item(target)
        if (efficiency := well_items[0].result.efficiency) is None:
            return None

        return CalculatedDocument(
            uuid=str(uuid4()),
            name="efficiency",
            value=efficiency,
            data_sources=[
                DataSource(feature="cycle threshold result", reference=well_item)
                for well_item in well_items
            ],
        )

    def iter_comparative_ct_calc_docs(self) -> Iterator[CalculatedDocument]:
        # Quantity, Quantity Mean, Quantity SD, Ct Mean, Ct SD, Delta Ct Mean,
        # Delta Ct SE, Delta Delta Ct, RQ, RQ min, RQ max
        for sample, target in self.view_st_data.iter_keys():
            if calc_doc := self.build_quantity_mean(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_quantity_sd(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_ct_sd(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_delta_ct_se(sample, target):
                yield from calc_doc.iter_struct()

            if target != self.r_target:
                if calc_doc := self.build_rq_min(sample, target):
                    yield from calc_doc.iter_struct()

                if calc_doc := self.build_rq_max(sample, target):
                    yield from calc_doc.iter_struct()

    def iter_standard_curve_calc_docs(self) -> Iterator[CalculatedDocument]:
        # Quantity, Quantity Mean, Quantity SD, Ct Mean, Ct SD, Y-Intercept,
        # R(superscript 2), Slope, Efficiency
        for sample, target in self.view_st_data.iter_keys():
            if calc_doc := self.build_quantity_mean(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_quantity_sd(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_ct_mean(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_ct_sd(sample, target):
                yield from calc_doc.iter_struct()

        for target in self.view_tr_data.data:
            if calc_doc := self.build_y_intercept(target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_r_squared(target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_slope(target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_efficiency(target):
                yield from calc_doc.iter_struct()

    def iter_relative_standard_curve_calc_docs(self) -> Iterator[CalculatedDocument]:
        # Quantity, Quantity Mean, Quantity SD, Ct Mean, Ct SD, Delta Ct Mean,
        # Delta Ct SE, Delta Delta Ct, RQ, RQ min, RQ max, Y-Intercept,
        # R(superscript 2), Slope, Efficiency
        for sample, target in self.view_st_data.iter_keys():
            if calc_doc := self.build_quantity_mean(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_quantity_sd(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_ct_sd(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_delta_ct_se(sample, target):
                yield from calc_doc.iter_struct()

            if target != self.r_target:
                if calc_doc := self.build_rq_min(sample, target):
                    yield from calc_doc.iter_struct()

                if calc_doc := self.build_rq_max(sample, target):
                    yield from calc_doc.iter_struct()

        for target in self.view_tr_data.data:
            if calc_doc := self.build_y_intercept(target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_r_squared(target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_slope(target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_efficiency(target):
                yield from calc_doc.iter_struct()

    def iter_presence_absence_calc_docs(self) -> Iterator[CalculatedDocument]:
        # Rn Mean, Rn SD
        for sample, target in self.view_st_data.iter_keys():
            if calc_doc := self.build_rn_mean(sample, target):
                yield from calc_doc.iter_struct()

            if calc_doc := self.build_rn_sd(sample, target):
                yield from calc_doc.iter_struct()

    def iter_calculated_data_documents(self) -> Iterator[CalculatedDocument]:
        if (
            self.experiment_type
            == ExperimentType.relative_standard_curve_qPCR_experiment
        ):
            yield from self.iter_relative_standard_curve_calc_docs()
        elif self.experiment_type == ExperimentType.comparative_CT_qPCR_experiment:
            yield from self.iter_comparative_ct_calc_docs()
        elif self.experiment_type == ExperimentType.standard_curve_qPCR_experiment:
            yield from self.iter_standard_curve_calc_docs()
        elif self.experiment_type == ExperimentType.presence_absence_qPCR_experiment:
            yield from self.iter_presence_absence_calc_docs()
