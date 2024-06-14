import pandas as pd

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
    TQuantityValueMilliSecond,
    TQuantityValueNumber,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.mabtech_apex.mabtech_apex_contents import MabtechApexContents
from allotropy.parsers.mabtech_apex.mabtech_apex_structure import (
    PlateInformation,
    Well,
    WellList,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class MabtechApexParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Mabtech Apex"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.CANDIDATE_RELEASE

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        raw_contents = pd.read_excel(named_file_contents.contents, sheet_name=None)
        contents = MabtechApexContents(raw_contents)
        data = PlateInformation.create(contents)
        wells = WellList.create(contents)
        return self._get_model(data, wells, named_file_contents.original_file_name)

    def _get_model(
        self, data: PlateInformation, wells: WellList, file_name: str
    ) -> Model:
        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier="N/A",
                    model_number=data.model_number,
                    equipment_serial_number=data.equipment_serial_number,
                ),
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    UNC_path=data.unc_path,
                    software_name="Apex",
                    software_version=data.software_version,
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                plate_reader_document=[
                    PlateReaderDocumentItem(
                        analyst=data.analyst,
                        measurement_aggregate_document=self.get_measurement_aggregate_document(
                            well
                        ),
                    )
                    for well in wells
                ],
            ),
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
        )

    def get_measurement_aggregate_document(
        self, well: Well
    ) -> MeasurementAggregateDocument:
        return MeasurementAggregateDocument(
            container_type=ContainerType.well_plate,
            plate_well_count=TQuantityValueNumber(value=float(96)),
            measurement_time=self._get_date_time(well.measurement_time),
            measurement_document=[self.get_measurement_document_item(well)],
        )

    def get_measurement_document_item(
        self, well: Well
    ) -> OpticalImagingMeasurementDocumentItems:
        return OpticalImagingMeasurementDocumentItems(
            measurement_identifier=random_uuid_str(),
            sample_document=self.get_sample_document(well),
            device_control_aggregate_document=OpticalImagingDeviceControlAggregateDocument(
                device_control_document=[
                    self.get_device_control_document_item(well),
                ]
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    self.get_processed_data_document(well),
                ]
            ),
        )

    def get_sample_document(self, well: Well) -> SampleDocument:
        return SampleDocument(
            sample_identifier=well.sample_identifier,
            location_identifier=well.location_identifier,
            well_plate_identifier=well.well_plate_identifier,
        )

    def get_device_control_document_item(
        self, well: Well
    ) -> OpticalImagingDeviceControlDocumentItem:
        return OpticalImagingDeviceControlDocumentItem(
            device_type="imager",
            detection_type="optical-imaging",
            exposure_duration_setting=(
                None
                if well.exposure_duration_setting is None
                else TQuantityValueMilliSecond(value=well.exposure_duration_setting)
            ),
            illumination_setting=(
                None
                if well.illumination_setting is None
                else TQuantityValueUnitless(value=well.illumination_setting)
            ),
        )

    def get_processed_data_document(self, well: Well) -> ProcessedDataDocumentItem:
        return ProcessedDataDocumentItem(
            processed_data_identifier=random_uuid_str(),
            image_feature_aggregate_document=ImageFeatureAggregateDocument(
                image_feature_document=[
                    ImageFeatureDocumentItem(
                        image_feature_identifier=random_uuid_str(),
                        image_feature_name=next(iter(image_feature.keys())),
                        image_feature_result=TQuantityValueUnitless(
                            value=image_feature[next(iter(image_feature.keys()))]
                        ),
                    )
                    for image_feature in well.image_features
                ]
            ),
        )
