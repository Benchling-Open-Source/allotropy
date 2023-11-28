from dataclasses import dataclass
from typing import Optional

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCountsPerMilliliter,
    TQuantityValueMicrometer,
    TQuantityValueMilliliter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TBooleanValue,
    TDateTimeValue,
    TIntValue,
    TStringValue,
)


@dataclass
class DistributionItem:
    cumulative_particle_density: TQuantityValueCountsPerMilliliter
    cumulative_count: TQuantityValueUnitless
    differential_count: TQuantityValueUnitless
    differential_particle_density: TQuantityValueCountsPerMilliliter
    particle_size: TQuantityValueMicrometer


@dataclass
class Distribution:
    items: Optional[list[DistributionItem]] = None


@dataclass
class DistributionDocument:
    data_processing_omission_setting: Optional[TBooleanValue] = None
    items: Optional[list[Distribution]] = None


@dataclass
class MeasurementDocument:
    distribution_document: Optional[DistributionDocument] = None


@dataclass
class Model:
    analyst: TStringValue
    detector_identifier: TStringValue
    detector_model_number: TStringValue
    detector_view_volume: TQuantityValueMilliliter
    dilution_factor_setting: TQuantityValueUnitless
    flush_volume_setting: TQuantityValueMilliliter
    measurement_time: TDateTimeValue
    repetition_setting: TIntValue
    sample_identifier: TStringValue
    sample_volume_setting: TQuantityValueMilliliter
    equipment_serial_number: Optional[TStringValue] = None
    model_numer: Optional[TStringValue] = None
    measurement_document: Optional[MeasurementDocument] = None
    measurement_identifier: Optional[TStringValue] = None
    manifest: str = "http://purl.allotrope.org/manifests/light-obscuration/REC/2021/12/light-obscuration.manifest"
