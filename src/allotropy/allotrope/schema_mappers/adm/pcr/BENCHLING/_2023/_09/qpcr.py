from collections.abc import Callable
from dataclasses import dataclass

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import (
    BaselineCorrectedReporterDataCube,
    CalculatedDataDocumentItem,
    ContainerType,
    DataProcessingDocument,
    DataProcessingDocument1,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ExperimentType,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    MeltingCurveDataCube,
    Model,
    NormalizedReporterDataCube,
    PassiveReferenceDyeDataCube,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    QPCRAggregateDocument,
    QPCRDocumentItem,
    ReporterDyeDataCube,
    SampleDocument,
    TCalculatedDataAggregateDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TNullableQuantityValueUnitless,
    TQuantityValueNumber,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
    TDateTimeValue,
)


@dataclass
class DataCubeComponent:
    type_: FieldComponentDatatype
    concept: str
    unit: str


@dataclass
class DataCube:
    label: str
    structure_dimensions: list[DataCubeComponent]
    structure_measures: list[DataCubeComponent]
    dimensions: list
    measures: list


@dataclass(frozen=True)
class DataSource:
    identifier: str
    feature: str


@dataclass(frozen=True)
class CalculatedDataItem:
    identifier: str
    name: str
    value: float
    unit: str
    data_sources: list[DataSource]


@dataclass
class Measurement:
    identifier: str
    timestamp: str
    target_identifier: str
    sample_identifier: str
    sample_role_type: str
    well_location_identifier: str
    well_plate_identifier: str
    total_cycle_number_setting: float
    pcr_detection_chemistry: str
    cycle_threshold_value_setting: float
    reporter_dye_setting: str | None = None
    quencher_dye_setting: str | None = None
    passive_reference_dye_setting: str | None = None
    automatic_cycle_threshold_enabled_setting: bool | None = None
    automatic_baseline_determination_enabled_setting: bool | None = None
    genotyping_determination_result: float | None = None
    cycle_threshold_result: float | None = None
    normalized_reporter_result: float | None = None
    baseline_corrected_reporter_result: float | None = None
    data_cubes: list[DataCube] | None = None


@dataclass(frozen=True)
class MeasurementGroup:
    measurements: list[Measurement]
    analyst: str
    experimental_data_identifier: str
    experiment_type: str
    container_type: ContainerType
    plate_well_count: float


@dataclass
class Metadata:
    device_identifier: str
    device_type: str
    device_serial_number: str
    model_number: str
    software_name: str
    software_version: str
    data_system_instance_identifier: str
    file_name: str
    unc_path: str


@dataclass
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


class Mapper:
    MANIFEST = "http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest"

    def __init__(
        self, asm_converter_name: str, get_date_time: Callable[[str], TDateTimeValue]
    ) -> None:
        self.converter_name = asm_converter_name
        self.get_date_time = get_date_time

    def map_model(self, data: Data, filename: str) -> Model:
        pass
