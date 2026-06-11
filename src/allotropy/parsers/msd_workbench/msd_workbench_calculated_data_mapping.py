from enum import Enum

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
)
from allotropy.calcdocs import (
    build_calc_docs,
    CalcDoc,
    FieldView,
    Measurement as CalcMeasurement,
    Node,
)
from allotropy.calcdocs.msd_workbench.extractor import MsdWorkbenchExtractor
from allotropy.parsers.msd_workbench.calculdated_data_structure import (
    CalculatedDataMeasurementStructure,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.pandas import SeriesData


class AggregatingProperty(Enum):
    ASSAY_IDENTIFIER = "assay identifier"
    SAMPLE_IDENTIFIER = "sample_identifier"
    WELL_PLATE_IDENTIFIER = "well_plate_identifier"
    LOCATION_IDENTIFIER = "location_identifier"
    WELL_PLATE_ID = "well_plate_identifier"


class CalculatedDataColumns(Enum):
    ADJUSTED_SIGNAL = "Adjusted Signal"
    MEAN = "Mean"
    ADJ_SIG_MEAN = "Adj. Sig. Mean"
    FIT_STATISTIC_RSQUARED = "Fit Statistic: RSquared"
    CV = "CV"
    PERCENT_RECOVERY = "% Recovery"
    PERCENT_RECOVERY_MEAN = "% Recovery Mean"
    CALC_CONCENTRATION = "Calc. Concentration"
    CALC_CONC_MEAN = "Calc. Conc. Mean"
    CALC_CONC_CV = "Calc. Conc. CV"


def create_calculated_data_groups(
    data: pd.DataFrame, measurements: list[Measurement]
) -> list[CalculatedDocument]:
    calc_data_measurements: list[CalculatedDataMeasurementStructure] = []
    for measurement in measurements:
        for _, row in data.iterrows():
            row_series = SeriesData(row)
            if measurement.well_location_identifier != row_series.get(
                str, "Well"
            ) or measurement.location_identifier != row_series.get(str, "Spot"):
                row_series.get_unread()
                continue
            calc_data_measurements.append(
                CalculatedDataMeasurementStructure(
                    measurement=measurement,
                    adjusted_signal=row_series.get(
                        float, CalculatedDataColumns.ADJUSTED_SIGNAL.value
                    ),
                    mean=row_series.get(float, CalculatedDataColumns.MEAN.value),
                    adj_sig_mean=row_series.get(
                        float, CalculatedDataColumns.ADJ_SIG_MEAN.value
                    ),
                    fit_statistic_rsquared=row_series.get(
                        float, CalculatedDataColumns.FIT_STATISTIC_RSQUARED.value
                    ),
                    cv=row_series.get(float, CalculatedDataColumns.CV.value),
                    percent_recovery=row_series.get(
                        float, CalculatedDataColumns.PERCENT_RECOVERY.value
                    ),
                    percent_recovery_mean=row_series.get(
                        float, CalculatedDataColumns.PERCENT_RECOVERY_MEAN.value
                    ),
                    calc_concentration=row_series.get(
                        float, CalculatedDataColumns.CALC_CONCENTRATION.value
                    ),
                    calc_conc_mean=row_series.get(
                        float, CalculatedDataColumns.CALC_CONC_MEAN.value
                    ),
                    calc_conc_cv=row_series.get(
                        float, CalculatedDataColumns.CALC_CONC_CV.value
                    ),
                )
            )
            # we do not need additional data for the calculated data documents
            row_series.get_unread()
    elements = MsdWorkbenchExtractor.get_elements(calc_data_measurements)
    views = {
        "sample_assay": FieldView(
            "sample_identifier", sub_view=FieldView("assay_identifier")
        ).apply(elements),
        "assay": FieldView("assay_identifier").apply(elements),
        "assay_plate_loc_sample": FieldView(
            "assay_identifier",
            sub_view=FieldView(
                "well_plate_identifier",
                sub_view=FieldView(
                    "location_identifier", sub_view=FieldView("sample_identifier")
                ),
            ),
        ).apply(elements),
    }
    nodes: list[Node] = [
        CalcMeasurement("luminescence", field="luminescence"),
        CalcDoc("Mean", field="mean", sources=["luminescence"], view="assay"),
        CalcDoc(
            CalculatedDataColumns.ADJUSTED_SIGNAL.value,
            field="adjusted_signal",
            sources=["luminescence"],
            view="sample_assay",
        ),
        CalcDoc(
            CalculatedDataColumns.ADJ_SIG_MEAN.value,
            field="adj_sig_mean",
            sources=["Mean"],
            view="assay",
        ),
        CalcDoc(
            "R-Squared",
            field="fit_statistic_rsquared",
            sources=["luminescence"],
            view="assay",
        ),
        CalcDoc(
            CalculatedDataColumns.CV.value,
            field="cv",
            sources=["luminescence"],
            view="assay",
        ),
        CalcDoc(
            CalculatedDataColumns.PERCENT_RECOVERY.value,
            field="percent_recovery",
            sources=["luminescence"],
            view="assay_plate_loc_sample",
        ),
        CalcDoc(
            CalculatedDataColumns.PERCENT_RECOVERY_MEAN.value,
            field="percent_recovery_mean",
            sources=[CalculatedDataColumns.PERCENT_RECOVERY.value],
            view="assay",
        ),
        CalcDoc(
            CalculatedDataColumns.CALC_CONCENTRATION.value,
            field="calc_concentration",
            sources=["luminescence"],
            view="assay_plate_loc_sample",
        ),
        CalcDoc(
            "Calc. Concentration Mean",
            field="calc_conc_mean",
            sources=[CalculatedDataColumns.CALC_CONCENTRATION.value],
            view="assay",
        ),
        CalcDoc(
            CalculatedDataColumns.CALC_CONC_CV.value,
            field="calc_conc_cv",
            sources=[CalculatedDataColumns.CALC_CONCENTRATION.value],
            view="assay",
        ),
    ]
    return build_calc_docs(nodes=nodes, views=views)
