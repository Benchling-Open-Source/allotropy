from dataclasses import dataclass

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
)


@dataclass
class CalculatedDataMeasurementStructure:
    measurement: Measurement
    adjusted_signal: float | None
    mean: float | None
    adj_sig_mean: float | None
    fit_statistic_rsquared: float | None
    cv: float | None
    percent_recovery: float | None
    percent_recovery_mean: float | None
    calc_concentration: float | None
    calc_conc_mean: float | None
