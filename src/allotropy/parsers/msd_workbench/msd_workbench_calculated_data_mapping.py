from enum import Enum

import pandas as pd

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
)
from allotropy.calcdocs.config import (
    CalcDocsConfig,
    CalculatedDataConfig,
    MeasurementConfig,
)
from allotropy.calcdocs.msd_workbench.extractor import MsdWorkbenchExtractor
from allotropy.calcdocs.msd_workbench.views import (
    AssayIdentifierView,
    LocationIdentifierView,
    SampleIdentifierView,
    WellPlateIdentifierView,
)
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
                )
            )
            # we do not need additional data for the calculated data documents
            row_series.get_unread()
    elements = MsdWorkbenchExtractor.get_elements(calc_data_measurements)
    sample_assay_view = SampleIdentifierView(sub_view=AssayIdentifierView()).apply(
        elements
    )
    assay_view = AssayIdentifierView().apply(elements)
    sample_well_plate_location_id_view = AssayIdentifierView(
        sub_view=WellPlateIdentifierView(
            sub_view=LocationIdentifierView(SampleIdentifierView())
        )
    ).apply(elements)
    measurement_conf = MeasurementConfig(
        name="luminescence",
        value="luminescence",
    )
    adj_signal_config = CalculatedDataConfig(
        name=CalculatedDataColumns.ADJUSTED_SIGNAL.value,
        value="adjusted_signal",
        view_data=sample_assay_view,
        source_configs=(measurement_conf,),
    )
    mean_config = CalculatedDataConfig(
        name=CalculatedDataColumns.MEAN.value,
        value="mean",
        view_data=assay_view,
        source_configs=(measurement_conf,),
    )
    adj_signal_mean_config = CalculatedDataConfig(
        name=CalculatedDataColumns.ADJ_SIG_MEAN.value,
        value="adj_sig_mean",
        view_data=assay_view,
        source_configs=(mean_config,),
    )
    rsquared_config = CalculatedDataConfig(
        name="R-Squared",
        value="fit_statistic_rsquared",
        view_data=assay_view,
        source_configs=(measurement_conf,),
    )
    cv_config = CalculatedDataConfig(
        name=CalculatedDataColumns.CV.value,
        value="cv",
        view_data=assay_view,
        source_configs=(measurement_conf,),
    )
    percent_recovery_config = CalculatedDataConfig(
        name=CalculatedDataColumns.PERCENT_RECOVERY.value,
        value="percent_recovery",
        view_data=sample_well_plate_location_id_view,
        source_configs=(measurement_conf,),
    )
    percent_recovery_mean_config = CalculatedDataConfig(
        name=CalculatedDataColumns.PERCENT_RECOVERY_MEAN.value,
        value="percent_recovery_mean",
        view_data=assay_view,
        source_configs=(percent_recovery_config,),
    )
    calc_concentration_config = CalculatedDataConfig(
        name=CalculatedDataColumns.CALC_CONCENTRATION.value,
        value="calc_concentration",
        view_data=sample_well_plate_location_id_view,
        source_configs=(measurement_conf,),
    )
    calc_conc_mean_config = CalculatedDataConfig(
        name="Calc. Concentration Mean",
        value="calc_conc_mean",
        view_data=assay_view,
        source_configs=(calc_concentration_config,),
    )
    configs = CalcDocsConfig(
        [
            mean_config,
            adj_signal_config,
            adj_signal_mean_config,
            rsquared_config,
            cv_config,
            percent_recovery_config,
            percent_recovery_mean_config,
            calc_concentration_config,
            calc_conc_mean_config,
        ]
    )
    calc_docs = [
        calc_doc
        for parent_calc_doc in configs.construct()
        for calc_doc in parent_calc_doc.iter_struct()
    ]
    return calc_docs
