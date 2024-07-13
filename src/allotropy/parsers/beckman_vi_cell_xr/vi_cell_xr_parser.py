from __future__ import annotations

import tempfile
import zipfile

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
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_reader import ViCellXRReader
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_structure import (
    Data,
    Metadata,
    Row,
)
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_txt_reader import ViCellXRTXTReader
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser
from allotropy.types import IOType


def remove_style_xml_file(contents: IOType) -> IOType:
    # Removes styles.xml from an xlsx file IO stream. xlsx files produced by VI-Cell XR
    # instrument may have an invalid <fill> tag in their styles.xml file which causes a
    # bug when reading with pandas (via openpyxl library).

    # zipfile only accepts a filename, so write contents to a named temp file.
    tmp = tempfile.NamedTemporaryFile()
    file_contents = contents.read()
    if isinstance(file_contents, str):
        file_contents = file_contents.encode()
    tmp.write(file_contents)

    # Write zip contents to a new file, skipping styles.xml
    new = tempfile.NamedTemporaryFile()
    with zipfile.ZipFile(tmp.name) as zin:
        with zipfile.ZipFile(new.name, "w") as zout:
            for item in zin.infolist():
                if item.filename == "xl/styles.xml":
                    continue
                zout.writestr(item, zin.read(item.filename))

    return open(new.name, "rb")


class ViCellXRParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Beckman Vi-Cell XR"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents
        filename = named_file_contents.original_file_name

        if filename.endswith("xlsx"):
            contents = remove_style_xml_file(contents)

        reader: ViCellXRTXTReader | ViCellXRReader
        if filename.endswith("txt"):
            reader = ViCellXRTXTReader(named_file_contents)
        else:
            reader = ViCellXRReader(contents)

        data = Data.create(reader)

        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/cell-counting/BENCHLING/2023/11/cell-counting.manifest",
            cell_counting_aggregate_document=CellCountingAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    model_number=data.metadata.model_number,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                cell_counting_document=[
                    self._get_cell_counting_document_item(row, data.metadata)
                    for row in data.rows
                ],
            ),
        )

    def _get_cell_counting_document_item(
        self, row: Row, metadata: Metadata
    ) -> CellCountingDocumentItem:
        return CellCountingDocumentItem(
            analyst=metadata.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_document=[
                    CellCountingDetectorMeasurementDocumentItem(
                        measurement_identifier=row.measurement_identifier,
                        measurement_time=self._get_date_time(row.timestamp),
                        sample_document=SampleDocument(
                            sample_identifier=row.sample_identifier
                        ),
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
                                    viable_cell_count=quantity_or_none(
                                        TQuantityValueCell, row.viable_cell_count
                                    ),
                                    average_total_cell_circularity=quantity_or_none(
                                        TQuantityValueUnitless,
                                        row.average_total_cell_circularity,
                                    ),
                                ),
                            ]
                        ),
                    )
                ],
            ),
        )
