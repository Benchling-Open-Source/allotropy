from typing import Union

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    DeviceSystemDocument,
    Model,
    PlateReaderAggregateDocument,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.revvity_kaleido.kaleido_structure import (
    Data,
)
from allotropy.parsers.revvity_kaleido.kaleido_structure_v2 import DataV2
from allotropy.parsers.revvity_kaleido.kaleido_structure_v3 import DataV3
from allotropy.parsers.vendor_parser import VendorParser


class KaleidoParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = Data.create(reader)
        return self._get_model(data)

    def _get_model(self, data: Union[DataV2, DataV3]) -> Model:
        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                plate_reader_document=[],
                device_system_document=self._get_device_system_document(data),
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
