from typing import Union

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    DataSystemDocument,
    DeviceSystemDocument,
    Model,
    PlateReaderAggregateDocument,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.revvity_kaleido.kaleido_builder import create_data
from allotropy.parsers.revvity_kaleido.kaleido_structure_v2 import DataV2
from allotropy.parsers.revvity_kaleido.kaleido_structure_v3 import DataV3
from allotropy.parsers.vendor_parser import VendorParser


class KaleidoParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = create_data(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(self, file_name: str, data: Union[DataV2, DataV3]) -> Model:
        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                plate_reader_document=[],
                device_system_document=self._get_device_system_document(data),
                data_system_document=self._get_data_system_document(
                    file_name, data.version
                ),
            ),
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
        )

    def _get_device_system_document(
        self, data: Union[DataV2, DataV3]
    ) -> DeviceSystemDocument:
        return DeviceSystemDocument(
            device_identifier="EnSight",
            model_number="EnSight",
            product_manufacturer="Revvity",
            equipment_serial_number=data.get_equipment_serial_number(),
        )

    def _get_data_system_document(
        self, file_name: str, version: str
    ) -> DataSystemDocument:
        return DataSystemDocument(
            file_name=file_name,
            software_name="Kaleido",
            software_version=version,
            ASM_converter_name=ASM_CONVERTER_NAME,
            ASM_converter_version=ASM_CONVERTER_VERSION,
        )
