from abc import ABC, abstractmethod
from typing import Union

from allotropy.allotrope.models.plate_reader_benchling_2023_09_plate_reader import (
    ContainerType,
    DataSystemDocument,
    DeviceSystemDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    FluorescencePointDetectionMeasurementDocumentItems,
    LuminescencePointDetectionDeviceControlAggregateDocument,
    LuminescencePointDetectionDeviceControlDocumentItem,
    LuminescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    OpticalImagingMeasurementDocumentItems,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    SampleDocument,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueRelativeLightUnit,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.revvity_kaleido.kaleido_builder import create_data
from allotropy.parsers.revvity_kaleido.kaleido_common_structure import WellPosition
from allotropy.parsers.revvity_kaleido.kaleido_structure_v2 import DataV2
from allotropy.parsers.revvity_kaleido.kaleido_structure_v3 import DataV3
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser

MeasurementItem = Union[
    OpticalImagingMeasurementDocumentItems,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
    FluorescencePointDetectionMeasurementDocumentItems,
    LuminescencePointDetectionMeasurementDocumentItems,
]


class MeasurementParser(ABC):
    @abstractmethod
    def parse(
        self, data: Union[DataV2, DataV3], well_position: WellPosition
    ) -> MeasurementItem:
        pass


class FluorescenceMeasurementParser(MeasurementParser):
    def parse(
        self, data: Union[DataV2, DataV3], well_position: WellPosition
    ) -> MeasurementItem:
        well_plate_identifier = data.get_well_plate_identifier()
        sample_identifier = (
            data.get_platemap_well_value(well_position)
            or f"{well_plate_identifier}_{well_position}"
        )
        return FluorescencePointDetectionMeasurementDocumentItems(
            measurement_identifier=random_uuid_str(),
            fluorescence=TQuantityValueRelativeFluorescenceUnit(
                value=data.get_well_value(well_position)
            ),
            sample_document=SampleDocument(
                sample_identifier=sample_identifier,
                location_identifier=str(well_position),
                well_plate_identifier=well_plate_identifier,
                sample_role_type=data.get_sample_role_type(well_position),
            ),
            device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    FluorescencePointDetectionDeviceControlDocumentItem(
                        device_type="",
                    ),
                ]
            ),
        )


class AbsorbanceMeasurementParser(MeasurementParser):
    def parse(
        self, data: Union[DataV2, DataV3], well_position: WellPosition
    ) -> MeasurementItem:
        well_plate_identifier = data.get_well_plate_identifier()
        sample_identifier = (
            data.get_platemap_well_value(well_position)
            or f"{well_plate_identifier}_{well_position}"
        )
        return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
            measurement_identifier=random_uuid_str(),
            absorbance=TQuantityValueMilliAbsorbanceUnit(
                value=data.get_well_value(well_position)
            ),
            sample_document=SampleDocument(
                sample_identifier=sample_identifier,
                location_identifier=str(well_position),
                well_plate_identifier=well_plate_identifier,
                sample_role_type=data.get_sample_role_type(well_position),
            ),
            device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type="",
                    ),
                ]
            ),
        )


class LuminescenceMeasurementParser(MeasurementParser):
    def parse(
        self, data: Union[DataV2, DataV3], well_position: WellPosition
    ) -> MeasurementItem:
        well_plate_identifier = data.get_well_plate_identifier()
        sample_identifier = (
            data.get_platemap_well_value(well_position)
            or f"{well_plate_identifier}_{well_position}"
        )
        return LuminescencePointDetectionMeasurementDocumentItems(
            measurement_identifier=random_uuid_str(),
            luminescence=TQuantityValueRelativeLightUnit(
                value=data.get_well_value(well_position)
            ),
            sample_document=SampleDocument(
                sample_identifier=sample_identifier,
                location_identifier=str(well_position),
                well_plate_identifier=well_plate_identifier,
                sample_role_type=data.get_sample_role_type(well_position),
            ),
            device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    LuminescencePointDetectionDeviceControlDocumentItem(
                        device_type="",
                    )
                ]
            ),
        )


class KaleidoParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = create_data(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(self, file_name: str, data: Union[DataV2, DataV3]) -> Model:
        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                plate_reader_document=self._get_plate_reader_document(data),
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

    def _get_plate_reader_document(
        self, data: Union[DataV2, DataV3]
    ) -> list[PlateReaderDocumentItem]:
        measurement_parser = self._get_measurement_document_parser(
            data.get_experiment_type()
        )
        return [
            PlateReaderDocumentItem(
                measurement_aggregate_document=self._get_measurement_aggregate_document(
                    data, measurement_parser, well_position
                )
            )
            for well_position in data.iter_wells()
        ]

    def _get_measurement_aggregate_document(
        self,
        data: Union[DataV2, DataV3],
        measurement_parser: MeasurementParser,
        well_position: WellPosition,
    ) -> MeasurementAggregateDocument:
        return MeasurementAggregateDocument(
            container_type=ContainerType.well_plate,
            measurement_time=self._get_date_time(data.get_measurement_time()),
            plate_well_count=TQuantityValueNumber(value=data.get_plate_well_count()),
            experiment_type=data.get_experiment_type(),
            analytical_method_identifier=data.get_analytical_method_id(),
            experimental_data_identifier=data.get_experimentl_data_id(),
            measurement_document=[measurement_parser.parse(data, well_position)],
        )

    def _get_measurement_document_parser(
        self, experiment_type: str
    ) -> MeasurementParser:
        experiment_type_lower = experiment_type.lower()
        if "fluorescence" in experiment_type_lower or "alpha" in experiment_type_lower:
            return FluorescenceMeasurementParser()
        elif "abs" in experiment_type_lower:
            return AbsorbanceMeasurementParser()
        elif "luminescence" in experiment_type_lower:
            return LuminescenceMeasurementParser()
        else:
            error = f"Unable to find valid experiment type in '{experiment_type}'"
            raise AllotropeConversionError(error)
