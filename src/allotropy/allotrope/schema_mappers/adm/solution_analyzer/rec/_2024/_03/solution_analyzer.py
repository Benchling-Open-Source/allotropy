from dataclasses import dataclass

from allotropy.allotrope.models.adm.solution_analyzer.rec._2024._03.solution_analyzer import (
    AnalyteAggregateDocument,
    AnalyteDocument,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    SolutionAnalyzerAggregateDocument,
    SolutionAnalyzerDocumentItem,
)
from allotropy.allotrope.schema_mappers.adm.bga.rec._2024._03.blood_gas_detector import (
    BloodGasDetectorMixin,
)
from allotropy.allotrope.schema_mappers.adm.cell_counting.rec._2024._03.cell_counting_detector import (
    CellCountingDetectorMixin,
)
from allotropy.allotrope.schema_mappers.adm.core.rec._2024._03.hierarchy import (
    HasDeviceSystemDocument,
    Measurement as CoreMeasurement,
    MeasurementGroup as CoreMeasurementGroup,
)
from allotropy.allotrope.schema_mappers.adm.metabolite_analyzer.rec._2024._03.metabolite_detector import (
    MetaboliteDetectorMixin,
)
from allotropy.allotrope.schema_mappers.adm.osmolality.rec._2024._03.osmolality_detector import (
    OsmolalityDetectorMixin,
)
from allotropy.allotrope.schema_mappers.adm.ph.rec._2024._03.ph_detector import (
    PhDetectorMixin,
)
from allotropy.allotrope.schema_mappers.adm.ultraviolet_absorbance.rec._2024._03.ultraviolet_absorbance_point_detection import (
    UltravioletAbsorbancePointDetectionMixin,
)
from allotropy.allotrope.schema_mappers.schema_mapper import SchemaMapper
from allotropy.constants import ASM_CONVERTER_VERSION


@dataclass(frozen=True, kw_only=True)
class MetaboliteDetectorMeasurement(MetaboliteDetectorMixin, CoreMeasurement):
    ...


@dataclass(frozen=True, kw_only=True)
class PhDetectorMeasurement(PhDetectorMixin, CoreMeasurement):
    ...


@dataclass(frozen=True, kw_only=True)
class UltravioletAbsorbancePointDetectionMeasurement(
    UltravioletAbsorbancePointDetectionMixin, CoreMeasurement
):
    ...


@dataclass(frozen=True, kw_only=True)
class BloodGasDetectorMeasurement(BloodGasDetectorMixin, CoreMeasurement):
    ...


@dataclass(frozen=True, kw_only=True)
class CellCountingDetectorMeasurement(CellCountingDetectorMixin, CoreMeasurement):
    ...


@dataclass(frozen=True, kw_only=True)
class OsmolalityDetectorMeasurement(OsmolalityDetectorMixin, CoreMeasurement):
    ...


Measurement = (
    OsmolalityDetectorMeasurement
    | MetaboliteDetectorMeasurement
    | PhDetectorMeasurement
    | UltravioletAbsorbancePointDetectionMeasurement
    | BloodGasDetectorMeasurement
    | CellCountingDetectorMeasurement
)


@dataclass(frozen=True, kw_only=True)
class MeasurementGroup(CoreMeasurementGroup):
    measurements: list[Measurement]
    data_processing_time: str | None


@dataclass(frozen=True, kw_only=True)
class HasDataSystemDocument:
    data_system_instance_identifier: str | None = None
    file_name: str | None = None
    unc_path: str | None = None
    software_name: str | None = None
    software_version: str | None = None

    def create_data_system_document(self, converter_name: str) -> DataSystemDocument:
        return DataSystemDocument(
            data_system_instance_identifier=self.data_system_instance_identifier,
            file_name=self.file_name,
            UNC_path=self.unc_path,
            software_name=self.software_name,
            software_version=self.software_version,
            ASM_converter_name=converter_name,
            ASM_converter_version=ASM_CONVERTER_VERSION,
        )


@dataclass(frozen=True, kw_only=True)
class Metadata(HasDeviceSystemDocument, HasDataSystemDocument):
    ...


@dataclass(frozen=True)
class Data:
    metadata: Metadata
    measurement_groups: list[MeasurementGroup]


class Mapper(SchemaMapper[Data, Model]):
    MANIFEST = "http://purl.allotrope.org/manifests/solution-analyzer/REC/2024/03/solution-analyzer.manifest"

    def map_model(self, data: Data) -> Model:
        return Model(
            solution_analyzer_aggregate_document=SolutionAnalyzerAggregateDocument(
                device_system_document=data.metadata.create_device_system_document(
                    DeviceSystemDocument
                ),
                data_system_document=data.metadata.create_data_system_document(
                    self.converter_name
                ),
                solution_analyzer_document=[
                    self._get_technique_document(measurement_group)
                    for measurement_group in data.measurement_groups
                ],
            ),
            field_asm_manifest=self.MANIFEST,
        )

    def _get_technique_document(
        self, measurement_group: MeasurementGroup
    ) -> SolutionAnalyzerDocumentItem:
        return SolutionAnalyzerDocumentItem(
            analyst=measurement_group.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                data_processing_time=self.get_date_time(
                    measurement_group.data_processing_time
                )
                if measurement_group.data_processing_time
                else None,
                measurement_document=[
                    measurement.create_measurement_document(
                        MeasurementDocument,
                        SampleDocument,
                        DeviceControlAggregateDocument,
                        DeviceControlDocumentItem,
                        ProcessedDataAggregateDocument,
                        ProcessedDataDocumentItem,
                        DataProcessingDocument,
                        AnalyteAggregateDocument,
                        AnalyteDocument,
                        self.get_date_time,
                    )
                    for measurement in measurement_group.measurements
                ],
            ),
        )
