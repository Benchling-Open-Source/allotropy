# header
# sample setup
# raw data
# amplification data
# multicomponent data
# results
# melt curve raw data

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional

from allotropy.allotrope.models.pcr_benchling_2023_09_qpcr import (
    ExperimentType,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio.calculated_document import CalculatedDocument
from allotropy.parsers.appbio_quantstudio.referenceable import Referenceable


@dataclass(frozen=True)
class Header:
    measurement_time: str
    plate_well_count: int
    experiment_type: ExperimentType
    device_identifier: str
    model_number: str
    device_serial_number: str
    measurement_method_identifier: str
    pcr_detection_chemistry: str
    passive_reference_dye_setting: Optional[str]
    barcode: Optional[str]
    analyst: Optional[str]
    experimental_data_identifier: Optional[str]


@dataclass
class WellItem(Referenceable):
    uuid: str
    identifier: int
    target_dna_description: str
    sample_identifier: str
    reporter_dye_setting: Optional[str]
    position: Optional[str]
    well_location_identifier: Optional[str]
    quencher_dye_setting: Optional[str]
    sample_role_type: Optional[str]
    amplification_data_obj: Optional[AmplificationData] = None
    result_obj: Optional[Result] = None

    def add_amplification_data(self, amplification_data: AmplificationData) -> None:
        self.amplification_data_obj = amplification_data

    @property
    def amplification_data(self) -> AmplificationData:
        if self.amplification_data_obj is None:
            msg = f"Unable to find amplification data for well {self.identifier}."
            raise AllotropeConversionError(msg)
        return self.amplification_data_obj

    def add_result(self, result: Result) -> None:
        self.result_obj = result

    @property
    def result(self) -> Result:
        if self.result_obj is None:
            msg = f"Unable to find result data for well {self.identifier}."
            raise AllotropeConversionError(msg)
        return self.result_obj


@dataclass
class Well:
    identifier: int
    items: dict[str, WellItem]
    multicomponent_data: Optional[MulticomponentData] = None
    melt_curve_raw_data: Optional[MeltCurveRawData] = None
    calculated_document: Optional[CalculatedDocument] = None

    def get_well_item(self, target: str) -> WellItem:
        well_item = self.items.get(target)
        if well_item is None:
            msg = f"Unable to find target DNA '{target}' for well {self.identifier}."
            raise AllotropeConversionError(msg)
        return well_item

    def get_an_well_item(self) -> Optional[WellItem]:
        if not self.items:
            return None
        target, *_ = self.items.keys()
        return self.items[target]

    def add_multicomponent_data(self, multicomponent_data: MulticomponentData) -> None:
        self.multicomponent_data = multicomponent_data

    def add_melt_curve_raw_data(self, melt_curve_raw_data: MeltCurveRawData) -> None:
        self.melt_curve_raw_data = melt_curve_raw_data


@dataclass(frozen=True)
class WellList:
    wells: list[Well]

    def iter_well_items(self) -> Iterator[WellItem]:
        for well in self.wells:
            yield from well.items.values()

    def __iter__(self) -> Iterator[Well]:
        return iter(self.wells)


@dataclass(frozen=True)
class RawData:
    lines: list[str]


@dataclass(frozen=True)
class AmplificationData:
    total_cycle_number_setting: float
    cycle: list[float]
    rn: list[Optional[float]]
    delta_rn: list[Optional[float]]


@dataclass(frozen=True)
class MulticomponentData:
    cycle: list[float]
    columns: dict[str, list[Optional[float]]]

    def get_column(self, name: str) -> list[Optional[float]]:
        column = self.columns.get(name)
        if column is None:
            msg = f"Unable to obtain '{name}' from multicomponent data."
            raise AllotropeConversionError(msg)
        return column


@dataclass(frozen=True)
class Result:
    cycle_threshold_value_setting: float
    cycle_threshold_result: Optional[float]
    automatic_cycle_threshold_enabled_setting: Optional[bool]
    automatic_baseline_determination_enabled_setting: Optional[bool]
    normalized_reporter_result: Optional[float]
    baseline_corrected_reporter_result: Optional[float]
    genotyping_determination_result: Optional[str]
    genotyping_determination_method_setting: Optional[float]
    quantity: Optional[float]
    quantity_mean: Optional[float]
    quantity_sd: Optional[float]
    ct_mean: Optional[float]
    ct_sd: Optional[float]
    delta_ct_mean: Optional[float]
    delta_ct_se: Optional[float]
    delta_delta_ct: Optional[float]
    rq: Optional[float]
    rq_min: Optional[float]
    rq_max: Optional[float]
    rn_mean: Optional[float]
    rn_sd: Optional[float]
    y_intercept: Optional[float]
    r_squared: Optional[float]
    slope: Optional[float]
    efficiency: Optional[float]


@dataclass(frozen=True)
class MeltCurveRawData:
    reading: list[float]
    fluorescence: list[Optional[float]]
    derivative: list[Optional[float]]


@dataclass(frozen=True)
class Data:
    header: Header
    wells: WellList
    raw_data: Optional[RawData]
    endogenous_control: str
    reference_sample: str
    calculated_documents: list[CalculatedDocument]
