from __future__ import annotations

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ContainerType,
    DataSystemDocument,
    DeviceSystemDocument,
    LuminescencePointDetectionDeviceControlAggregateDocument,
    LuminescencePointDetectionDeviceControlDocumentItem,
    LuminescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueNumber,
    TQuantityValueRelativeLightUnit,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.methodical_mind.methodical_mind_structure import (
    CombinedData,
    PlateData,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser

LUMINESCENCE = "luminescence"
LUMINESCENCE_DETECTOR = "luminescence detector"


class MethodicalMindParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Methodical Mind"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        file_lines = read_to_lines(named_file_contents)
        reader = CsvReader(file_lines)
        combined_data = CombinedData.create(reader)
        return self._get_model(combined_data)

    def _get_model(self, combined_data: CombinedData) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=self._get_device_system_document(combined_data),
                data_system_document=self._get_data_system_document(combined_data),
                plate_reader_document=self._get_plate_reader_document(
                    combined_data.plate_doc_info
                ),
            ),
        )

    def _get_device_system_document(
        self, combined_data: CombinedData
    ) -> DeviceSystemDocument:
        return DeviceSystemDocument(
            device_identifier=NOT_APPLICABLE,
            model_number=combined_data.model,
            equipment_serial_number=combined_data.serial_number,
        )

    def _get_data_system_document(
        self, combined_data: CombinedData
    ) -> DataSystemDocument:
        return DataSystemDocument(
            file_name=combined_data.file_name.rsplit("\\", 1)[-1],
            UNC_path=combined_data.file_name,
            software_name=combined_data.version,
            software_version=combined_data.version,
            ASM_converter_name=self.get_asm_converter_name(),
            ASM_converter_version=ASM_CONVERTER_VERSION,
        )

    def _get_plate_reader_document(
        self, plate_docs: list[PlateData]
    ) -> list[PlateReaderDocumentItem]:
        plate_reader_docs = []
        for plate in plate_docs:
            for well in plate.well_data:
                plate_reader_doc = PlateReaderDocumentItem(
                    analyst=plate.analyst,
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_time=self._get_date_time(plate.measurement_time),
                        container_type=ContainerType.well_plate,
                        plate_well_count=TQuantityValueNumber(
                            value=plate.plate_well_count
                        ),
                        measurement_document=[
                            LuminescencePointDetectionMeasurementDocumentItems(
                                measurement_identifier=random_uuid_str(),
                                luminescence=TQuantityValueRelativeLightUnit(
                                    value=well.luminescence
                                ),
                                sample_document=SampleDocument(
                                    sample_identifier=well.sample_identifier,
                                    location_identifier=well.location_identifier,
                                    well_plate_identifier=plate.well_plate_id,
                                ),
                                device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                                    device_control_document=[
                                        LuminescencePointDetectionDeviceControlDocumentItem(
                                            device_type=LUMINESCENCE_DETECTOR,
                                            detection_type=LUMINESCENCE,
                                        )
                                    ]
                                ),
                            )
                        ],
                    ),
                )
                plate_reader_docs.append(plate_reader_doc)
        return plate_reader_docs
