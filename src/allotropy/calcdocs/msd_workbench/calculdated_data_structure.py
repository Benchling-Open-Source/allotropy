from dataclasses import dataclass

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
)


@dataclass
class CalculatedDataMeasurementStructure:
    measurement: Measurement
    adjusted_signal: float
    mean: float
    adj_sig_mean: float
    fit_statistic_rsquared: float
    cv: float
    percent_recovery: float
    percent_recovery_mean: float
    calc_concentration: float
    calc_conc_mean: float
