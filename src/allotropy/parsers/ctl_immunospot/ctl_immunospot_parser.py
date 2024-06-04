from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ContainerType,
    DataSystemDocument,
    DeviceSystemDocument,
    ImageFeatureAggregateDocument,
    ImageFeatureDocumentItem,
    MeasurementAggregateDocument,
    Model,
    OpticalImagingDeviceControlAggregateDocument,
    OpticalImagingDeviceControlDocumentItem,
    OpticalImagingMeasurementDocumentItems,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueNumber,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.ctl_immunospot.ctl_immunospot_structure import Data, Well
from allotropy.parsers.lines_reader import LinesReader, read_to_lines
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class CtlImmunospotParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "CTL ImmunoSpot"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = LinesReader(lines)
        data = Data.create(reader)
        return self._get_model(data)

    def _get_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
            plate_reader_aggregate_document=self._get_plate_reader_aggregate_document(
                data
            ),
        )

    def _get_plate_reader_aggregate_document(
        self, data: Data
    ) -> PlateReaderAggregateDocument:
        return PlateReaderAggregateDocument(
            device_system_document=self._get_device_system_document(data),
            data_system_document=self._get_data_system_document(data),
            plate_reader_document=[
                self._get_plate_reader_document_item(data, well)
                for well in data.assay_data.iter_wells()
            ],
        )

    def _get_device_system_document(self, data: Data) -> DeviceSystemDocument:
        return DeviceSystemDocument(
            device_identifier=data.device_info.device_identifier,
            model_number=data.device_info.model_number,
            product_manufacturer="CTL",
            equipment_serial_number=data.device_info.equipment_serial_number,
        )

    def _get_data_system_document(self, data: Data) -> DataSystemDocument:
        return DataSystemDocument(
            data_system_instance_identifier=data.device_info.data_system_instance_id,
            file_name=data.device_info.basename,
            UNC_path=data.device_info.unc_path,
            software_name=data.device_info.software_name,
            software_version=data.device_info.software_version,
            ASM_converter_name=ASM_CONVERTER_NAME,
            ASM_converter_version=ASM_CONVERTER_VERSION,
        )

    def _get_plate_reader_document_item(
        self, data: Data, well: Well
    ) -> PlateReaderDocumentItem:
        return PlateReaderDocumentItem(
            analyst=data.device_info.analyst,
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self._get_date_time(data.device_info.measurement_time),
                container_type=ContainerType.well_plate,
                plate_well_count=TQuantityValueNumber(value=data.assay_data.well_count),
                measurement_document=[self._get_measurement_document(data, well)],
            ),
        )

    def _get_measurement_document(
        self, data: Data, well: Well
    ) -> OpticalImagingMeasurementDocumentItems:
        return OpticalImagingMeasurementDocumentItems(
            measurement_identifier=random_uuid_str(),
            device_control_aggregate_document=OpticalImagingDeviceControlAggregateDocument(
                device_control_document=[
                    OpticalImagingDeviceControlDocumentItem(
                        device_type="imager",
                        detection_type="optical-imaging",
                    )
                ]
            ),
            sample_document=self._get_sample_document(data, well),
            processed_data_aggregate_document=self._get_processed_data_aggregate_document(
                data, well
            ),
        )

    def _get_sample_document(self, data: Data, well: Well) -> SampleDocument:
        well_plate_identifier = data.get_plate_identifier()
        return SampleDocument(
            sample_identifier=f"{well_plate_identifier}_{well.pos}",
            location_identifier=well.pos,
            well_plate_identifier=well_plate_identifier,
        )

    def _get_processed_data_aggregate_document(
        self, data: Data, well: Well
    ) -> ProcessedDataAggregateDocument:
        return ProcessedDataAggregateDocument(
            processed_data_document=[
                ProcessedDataDocumentItem(
                    processed_data_identifier=random_uuid_str(),
                    image_feature_aggregate_document=ImageFeatureAggregateDocument(
                        image_feature_document=[
                            ImageFeatureDocumentItem(
                                image_feature_identifier=random_uuid_str(),
                                image_feature_name=plate.name,
                                image_feature_result=TQuantityValueUnitless(
                                    value=plate.get_well(well.pos).value
                                    or InvalidJsonFloat.NaN
                                ),
                            )
                            for plate in data.assay_data.plates
                        ],
                    ),
                )
            ]
        )
