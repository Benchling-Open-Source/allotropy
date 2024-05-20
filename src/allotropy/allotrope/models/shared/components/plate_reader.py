from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from allotropy.allotrope.models.shared.definitions.definitions import (
    TDatacube,
    TStringValue,
)


class SampleRoleType(Enum):
    control_sample_role = "control sample role"
    standard_sample_role = "standard sample role"
    validation_sample_role = "validation sample role"
    experiment_sample_role = "experiment sample role"
    sample_role = "sample role"
    spiked_sample_role = "spiked sample role"
    blank_role = "blank role"
    unknown_sample_role = "unknown sample role"
    calibration_sample_role = "calibration sample role"
    unspiked_sample_role = "unspiked sample role"
    specimen_role = "specimen role"
    quality_control_sample_role = "quality control sample role"
    reference_sample_role = "reference sample role"


@dataclass
class SampleDocument:
    well_location_identifier: TStringValue
    sample_identifier: TStringValue | None = None
    batch_identifier: TStringValue | None = None
    sample_role_type: SampleRoleType | None = None
    # TODO: plate_barcode isn't actually in the schema yet, needs to be modified to add it.
    plate_barcode: str | None = None


@dataclass
class ProcessedDataDocumentItem:
    processed_data: float | str | TDatacube
    data_format_specification_type: TStringValue | None = None
    data_processing_description: TStringValue | None = None


@dataclass
class ProcessedDataAggregateDocument:
    processed_data_document: list[ProcessedDataDocumentItem] | None = None
