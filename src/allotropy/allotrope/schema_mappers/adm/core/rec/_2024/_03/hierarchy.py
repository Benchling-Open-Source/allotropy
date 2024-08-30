from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.parsers.utils.values import assert_not_none

T = TypeVar("T")
AggDocumentClass = TypeVar("AggDocumentClass")
DocumentClass = TypeVar("DocumentClass")
DocumentClass1 = TypeVar("DocumentClass1")
DocumentClass2 = TypeVar("DocumentClass2")
DocumentClass3 = TypeVar("DocumentClass3")
DocumentClass4 = TypeVar("DocumentClass4")
DocumentClass5 = TypeVar("DocumentClass5")
DocumentClass6 = TypeVar("DocumentClass6")
DocumentClass7 = TypeVar("DocumentClass7")
DocumentClass8 = TypeVar("DocumentClass8")
Type = Callable[..., T]


@dataclass(frozen=True)
class Error:
    error: str
    feature: str | None = None


@dataclass(frozen=True, kw_only=True)
class HasErrors:
    errors: list[Error] | None = None

    def create_error_aggregate_document(
        self, agg_doc: Type[AggDocumentClass], item_doc: Type[DocumentClass]
    ) -> AggDocumentClass | None:
        if not self.errors:
            return None

        return agg_doc(
            error_document=[
                item_doc(error=error.error, error_feature=error.feature)
                for error in self.errors
            ]
        )


@dataclass(frozen=True, kw_only=True)
class HasSampleDocument:
    description: str | None = None
    sample_identifier: str
    batch_identifier: str | None = None
    sample_role_type: str | None = None
    written_name: str | None = None

    def create_sample_document(self, doc: Type[DocumentClass]) -> DocumentClass:
        return doc(
            sample_identifier=self.sample_identifier,
            description=self.description,
            batch_identifier=self.batch_identifier,
            sample_role_type=self.sample_role_type,
            written_name=self.written_name,
        )


@dataclass(frozen=True, kw_only=True)
class HasDeviceControlDocument:
    # Device control document
    device_type: str
    device_identifier: str | None = None
    detection_type: str | None = None
    product_manufacturer: str | None = None
    brand_name: str | None = None
    equipment_serial_number: str | None = None
    model_number: str | None = None
    firmware_version: str | None = None

    def device_control_document_kwargs(self) -> dict[str, Any]:
        return {}

    def create_device_control_document(
        self, agg_doc: Type[AggDocumentClass], item_doc: Type[DocumentClass]
    ) -> AggDocumentClass:
        return agg_doc(
            device_control_document=[
                item_doc(
                    device_type=self.device_type,
                    device_identifier=self.device_identifier,
                    detection_type=self.detection_type,
                    product_manufacturer=self.product_manufacturer,
                    brand_name=self.brand_name,
                    equipment_serial_number=self.equipment_serial_number,
                    model_number=self.model_number,
                    firmware_version=self.firmware_version,
                    **self.device_control_document_kwargs(),
                )
            ]
        )


@dataclass(frozen=True, kw_only=True)
class HasDeviceSystemDocument:
    asset_management_identifier: str | None = None
    description: str | None = None
    brand_name: str | None = None
    product_manufacturer: str | None = None
    device_identifier: str | None = None
    model_number: str | None = None
    equipment_serial_number: str | None = None
    firmware_version: str | None = None
    # devices: list[Device] | None = None

    def create_device_system_document(
        self, document_cls: Type[DocumentClass]
    ) -> DocumentClass:
        return document_cls(
            asset_management_identifier=self.asset_management_identifier,
            description=self.description,
            brand_name=self.brand_name,
            product_manufacturer=self.product_manufacturer,
            device_identifier=self.device_identifier,
            model_number=self.model_number,
            equipment_serial_number=self.equipment_serial_number,
            firmware_version=self.firmware_version,
        )


@dataclass(frozen=True, kw_only=True)
class HasDataProcessingDocument:
    def data_processing_document_kwargs(self) -> dict[str, Any]:
        return {}

    def create_data_processing_document(
        self, document_cls: Type[DocumentClass]
    ) -> DocumentClass | None:
        kwargs = self.data_processing_document_kwargs()
        if not kwargs:
            return None
        return document_cls(
            **self.data_processing_document_kwargs(),
        )


@dataclass(frozen=True, kw_only=True)
class HasDataSourceDocument:
    asset_management_identifier: str | None = None
    description: str | None = None
    brand_name: str | None = None
    product_manufacturer: str | None = None
    device_identifier: str | None = None
    model_number: str | None = None
    equipment_serial_number: str | None = None
    firmware_version: str | None = None
    # devices: list[Device] | None = None

    def create_data_source_document(
        self, document_cls: Type[DocumentClass]
    ) -> DocumentClass:
        return document_cls(
            asset_management_identifier=self.asset_management_identifier,
            description=self.description,
            brand_name=self.brand_name,
            product_manufacturer=self.product_manufacturer,
            device_identifier=self.device_identifier,
            model_number=self.model_number,
            equipment_serial_number=self.equipment_serial_number,
            firmware_version=self.firmware_version,
        )


@dataclass(frozen=True, kw_only=True)
class HasProcessedDataDocument(HasDataProcessingDocument, HasDataSourceDocument):
    processed_data_identifier: str | None = None

    def processed_data_document_kwargs(self) -> dict[str, Any]:
        return {}

    def create_processed_data_document(
        self,
        agg_doc: Type[AggDocumentClass],
        item_doc: Type[DocumentClass],
        data_doc: Type[DocumentClass2],
    ) -> AggDocumentClass | None:
        kwargs = {
            "processed_data_identifier": self.processed_data_identifier,
            "data_processing_document": self.create_data_processing_document(data_doc),
        }
        kwargs |= self.processed_data_document_kwargs()
        if not any(value for value in kwargs.values()):
            return None
        return agg_doc(processed_data_document=[item_doc(**kwargs)])


@dataclass(frozen=True, kw_only=True)
class Measurement(
    HasSampleDocument, HasDeviceControlDocument, HasProcessedDataDocument, HasErrors
):
    # Measurement metadata
    measurement_time: str | None = None
    identifier: str | None = None

    # processed_data: list[ProcessedData] | None = None
    # calculated_data: list[CalculatedData] | None = None
    # statistics: list[Statistic] | None = None
    # images: list[Image] | None = None

    def measurement_kwargs(self, **_: Any) -> dict[str, Any]:
        return {}

    def create_measurement_document(
        self,
        measurement_doc: Type[DocumentClass],
        sample_doc: Type[DocumentClass1],
        device_control_agg_doc: Type[DocumentClass2],
        device_control_item_doc: Type[DocumentClass3],
        processed_data_agg_doc: Type[DocumentClass4],
        processed_data_item_doc: Type[DocumentClass5],
        data_processing_doc: Type[DocumentClass6],
        analyte_agg_doc: Type[DocumentClass7],
        analyte_item_doc: Type[DocumentClass8],
        get_date_time: Callable[[str], TDateTimeValue],
    ) -> DocumentClass:
        return measurement_doc(
            measurement_identifier=assert_not_none(
                self.identifier, "measurement identifier"
            ),
            measurement_time=get_date_time(
                assert_not_none(self.measurement_time, "measurement time")
            ),
            sample_document=self.create_sample_document(sample_doc),
            device_control_aggregate_document=self.create_device_control_document(
                device_control_agg_doc,
                device_control_item_doc,
            ),
            processed_data_aggregate_document=self.create_processed_data_document(
                processed_data_agg_doc,
                processed_data_item_doc,
                data_processing_doc,
            ),
            **self.measurement_kwargs(
                analyte_agg_doc=analyte_agg_doc, analyte_item_doc=analyte_item_doc
            ),
        )


@dataclass(frozen=True, kw_only=True)
class MeasurementGroup(HasErrors):
    analyst: str | None = None
    submitter: str | None = None

    # diagnostic_traces: list[DiagnosticTrace] | None = None
    # processed_data: list[ProcessedData] | None = None
    # calculated_data: list[CalculatedData] | None = None
    # statistics: list[Statistic] | None = None
    # images: list[Image] | None = None
