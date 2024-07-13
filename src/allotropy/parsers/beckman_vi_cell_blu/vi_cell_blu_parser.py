from __future__ import annotations

from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    CellCountingAggregateDocument,
    CellCountingDetectorDeviceControlAggregateDocument,
    CellCountingDetectorMeasurementDocumentItem,
    CellCountingDocumentItem,
    DataProcessingDocument,
    DataSystemDocument,
    DeviceControlDocumentItemModel,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    Model,
    ProcessedDataAggregateDocument1,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCell,
    TQuantityValueMicrometer,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValuePercent,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_reader import ViCellBluReader
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_structure import (
    Data,
    Metadata,
    Row,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser


class ViCellBluParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Beckman Vi-Cell BLU"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        return self._get_model(
            data=Data.create(ViCellBluReader.read(named_file_contents)),
            filename=named_file_contents.original_file_name,
        )

    def _get_model(self, data: Data, filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest",
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=data.metadata.software_name,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                cell_counting_document=self._get_cell_counting_document(data),
            ),
        )

    def _get_cell_counting_document(
        self, data: Data
    ) -> list[CellCountingDocumentItem]:
        """
        return [
            self._get_cell_counting_document_item(row, metadata)
            for i in range(len(data.index))
            if (_Sample(data, i).get_value("Cell count"))
        ]
        """
        return [
            self._get_cell_counting_document_item(row, data.metadata)
            for row in data.rows
        ]

    def _get_cell_counting_document_item(
        self, row: Row, metadata: Metadata
    ) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=row.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_time=self._get_date_time(row.timestamp),
                        measurement_identifier=row.measurement_identifier,
                        sample_document=SampleDocument(sample_identifier=row.sample_identifier),
                        device_control_aggregate_document=CellCountingDetectorDeviceControlAggregateDocument(
                            device_control_document=[
                                DeviceControlDocumentItemModel(
                                    device_type=metadata.device_type,
                                    detection_type=metadata.detection_type,
                                )
                            ]
                        ),
                        processed_data_aggregate_document=ProcessedDataAggregateDocument1(
                            processed_data_document=[
                                ProcessedDataDocumentItem(
                                    data_processing_document=DataProcessingDocument(
                                        cell_type_processing_method=row.cell_type_processing_method,
                                        minimum_cell_diameter_setting=quantity_or_none(
                                            TQuantityValueMicrometer,
                                            row.minimum_cell_diameter_setting,
                                        ),
                                        maximum_cell_diameter_setting=quantity_or_none(
                                            TQuantityValueMicrometer,
                                            row.maximum_cell_diameter_setting,
                                        ),
                                        cell_density_dilution_factor=quantity_or_none(
                                            TQuantityValueUnitless,
                                            row.cell_density_dilution_factor,
                                        ),
                                    ),
                                    viability__cell_counter_=TQuantityValuePercent(
                                        value=row.viability
                                    ),
                                    viable_cell_density__cell_counter_=TQuantityValueMillionCellsPerMilliliter(
                                        value=row.viable_cell_density
                                    ),
                                    total_cell_count=quantity_or_none(
                                        TQuantityValueCell, row.total_cell_count
                                    ),
                                    total_cell_density__cell_counter_=quantity_or_none(
                                        TQuantityValueMillionCellsPerMilliliter,
                                        row.total_cell_density,
                                    ),
                                    average_total_cell_diameter=quantity_or_none(
                                        TQuantityValueMicrometer,
                                        row.average_total_cell_diameter,
                                    ),
                                    average_live_cell_diameter__cell_counter_=quantity_or_none(
                                        TQuantityValueMicrometer,
                                        row.average_live_cell_diameter,
                                    ),
                                    viable_cell_count=quantity_or_none(
                                        TQuantityValueCell, row.viable_cell_count
                                    ),
                                    average_total_cell_circularity=quantity_or_none(
                                        TQuantityValueUnitless,
                                        row.average_total_cell_circularity,
                                    ),
                                    average_viable_cell_circularity=quantity_or_none(
                                        TQuantityValueUnitless,
                                        row.average_viable_cell_circularity,
                                    ),
                                ),
                            ]
                        ),
                    )
                ],
            ),
        )
