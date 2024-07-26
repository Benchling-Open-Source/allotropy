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
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicrometer,
    TQuantityValueMillionCellsPerMilliliter,
    TQuantityValuePercent,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.chemometec_nucleoview.constants import (
    NUCLEOCOUNTER_DETECTION_TYPE,
    NUCLEOCOUNTER_DEVICE_TYPE,
    NUCLEOCOUNTER_SOFTWARE_NAME,
)
from allotropy.parsers.chemometec_nucleoview.nucleoview_reader import NucleoviewReader
from allotropy.parsers.chemometec_nucleoview.nucleoview_structure import Row
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser


class ChemometecNucleoviewParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "ChemoMetec Nucleoview"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents
        filename = named_file_contents.original_file_name
        rows = Row.create_rows(NucleoviewReader.read(contents))
        return self._get_model(rows, filename)

    def _get_model(self, rows: list[Row], filename: str) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest",
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=rows[0].model_number,
                    equipment_serial_number=rows[0].equipment_serial_number,
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=NUCLEOCOUNTER_SOFTWARE_NAME,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                    software_version=rows[0].software_version,
                ),
                cell_counting_document=[
                    self._get_cell_counting_document_item(row) for row in rows
                ],
            ),
        )

    def _get_cell_counting_document_item(self, row: Row) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=row.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_identifier=random_uuid_str(),
                        measurement_time=self._get_date_time(row.timestamp),
                        sample_document=SampleDocument(
                            sample_identifier=row.sample_identifier
                        ),
                        device_control_aggregate_document=CellCountingDetectorDeviceControlAggregateDocument(
                            device_control_document=[
                                DeviceControlDocumentItemModel(
                                    device_type=NUCLEOCOUNTER_DEVICE_TYPE,
                                    detection_type=NUCLEOCOUNTER_DETECTION_TYPE,
                                )
                            ]
                        ),
                        processed_data_aggregate_document=ProcessedDataAggregateDocument(
                            processed_data_document=[
                                ProcessedDataDocumentItem(
                                    data_processing_document=DataProcessingDocument(
                                        cell_density_dilution_factor=quantity_or_none(
                                            TQuantityValueUnitless,
                                            row.multiplication_factor,
                                        )
                                    ),
                                    viability__cell_counter_=TQuantityValuePercent(
                                        value=row.viability_percent
                                    ),
                                    viable_cell_density__cell_counter_=TQuantityValueMillionCellsPerMilliliter(
                                        value=row.live_cell_count
                                    ),
                                    dead_cell_density__cell_counter_=quantity_or_none(
                                        TQuantityValueMillionCellsPerMilliliter,
                                        row.dead_cell_count,
                                    ),
                                    total_cell_density__cell_counter_=quantity_or_none(
                                        TQuantityValueMillionCellsPerMilliliter,
                                        row.total_cell_count,
                                    ),
                                    average_total_cell_diameter=quantity_or_none(
                                        TQuantityValueMicrometer,
                                        row.estimated_cell_diameter,
                                    ),
                                )
                            ]
                        ),
                    )
                ],
            ),
        )
