from enum import Enum
from io import IOBase
from typing import Any, Dict, Optional, TypeAlias, TypeVar, Union
import uuid

from allotropy.allotrope.allotrope import AllotropyError
from allotropy.allotrope.models.plate_reader_rec_2023_09_plate_reader import (
    ContainerType,
    DeviceControlDocument,
    DeviceSystemDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    FluorescencePointDetectionMeasurementDocumentItems,
    LuminescencePointDetectionDeviceControlAggregateDocument,
    LuminescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    SampleDocument,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMillimeter,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TRelativeFluorescenceUnit,
    TRelativeLightUnit,
)
from allotropy.allotrope.models.shared.definitions.definitions import TDateTimeValue
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    Data,
    Plate,
    PlateMap,
    Result,
)
from allotropy.parsers.vendor_parser import VendorParser

T = TypeVar("T")


class ReadType(Enum):
    ABSORBANCE = "Absorbance"
    FLUORESCENCE = "Fluorescence"
    LUMINESCENCE = "Luminescence"


MeasurementDocumentItemsType: TypeAlias = Union[
    type[UltravioletAbsorbancePointDetectionMeasurementDocumentItems],
    type[FluorescencePointDetectionMeasurementDocumentItems],
    type[LuminescencePointDetectionMeasurementDocumentItems],
]

MeasurementDocumentItems: TypeAlias = Union[
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
    FluorescencePointDetectionMeasurementDocumentItems,
    LuminescencePointDetectionMeasurementDocumentItems,
]

DeviceControlAggregateDocumentType: TypeAlias = Union[
    type[UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument],
    type[FluorescencePointDetectionDeviceControlAggregateDocument],
    type[LuminescencePointDetectionDeviceControlAggregateDocument],
]

DeviceControlAggregateDocument: TypeAlias = Union[
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    LuminescencePointDetectionDeviceControlAggregateDocument,
]

MeasurementUnitType: TypeAlias = Union[
    type[TRelativeFluorescenceUnit],
    type[TRelativeLightUnit],
    type[TQuantityValueMilliAbsorbanceUnit],
]

MeasurementUnit: TypeAlias = Union[
    TRelativeFluorescenceUnit,
    TRelativeLightUnit,
    TQuantityValueMilliAbsorbanceUnit,
]


READ_TYPE_TO_MEASUREMENT_DOCUMENT_ITEMS: Dict[ReadType, MeasurementDocumentItemsType] = {
    ReadType.ABSORBANCE: UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
    ReadType.FLUORESCENCE: FluorescencePointDetectionMeasurementDocumentItems,
    ReadType.LUMINESCENCE: LuminescencePointDetectionMeasurementDocumentItems,
}

READ_TYPE_TO_DEVICE_CONTROL_AGGREGATE_DOCUMENT: Dict[ReadType, DeviceControlAggregateDocumentType] = {
    ReadType.ABSORBANCE: UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    ReadType.FLUORESCENCE: FluorescencePointDetectionDeviceControlAggregateDocument,
    ReadType.LUMINESCENCE: LuminescencePointDetectionDeviceControlAggregateDocument,
}

READ_TYPE_TO_MEASUREMENT_UNIT: Dict[ReadType, MeasurementUnitType] = {
    ReadType.ABSORBANCE: TQuantityValueMilliAbsorbanceUnit,
    ReadType.FLUORESCENCE: TRelativeFluorescenceUnit,
    ReadType.LUMINESCENCE: TRelativeLightUnit,
}


def safe_value(cls: type[T], value: Optional[Any]) -> Optional[T]:
    return None if value is None else cls(value=value)  # type: ignore[call-arg]


class PerkinElmerEnvisionParser(VendorParser):
    def _parse(self, raw_contents: IOBase, _: str) -> Model:
        reader = CsvReader(raw_contents)
        return self._get_model(Data.create(reader))

    def _get_model(self, data: Data) -> Model:
        if data.number_of_wells is None:
            msg = "Unable to get number of the wells in the plate"
            raise AllotropyError(msg)

        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                plate_reader_document=self._get_plate_reader_document(data),
                device_system_document=DeviceSystemDocument(
                    asset_management_identifier=data.instrument.serial_number,  # TODO verify what this should be
                    model_number=data.instrument.serial_number,
                    device_identifier=data.instrument.nickname,
                )
            ),
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/REC/2023/09/plate-reader.manifest",
        )

    def _get_read_type(self, data: Data) -> ReadType:
        patterns = {
            "ABS": ReadType.ABSORBANCE,
            "Absorbance": ReadType.ABSORBANCE,
            "LUM": ReadType.LUMINESCENCE,
            "Luminescence": ReadType.LUMINESCENCE,
            "Fluorescence": ReadType.FLUORESCENCE,
        }

        for key in patterns:
            if key in data.labels.label:
                return patterns[key]

        return ReadType.FLUORESCENCE  # TODO check if this is correct, this is the original behavior

    def _get_measurement_time(self, data: Data) -> TDateTimeValue:
        dates = [
            plate.plate_info.measurement_time
            for plate in data.plates
            if plate.plate_info.measurement_time
        ]

        if dates:
            return self.get_date_time(min(dates))

        msg = "Unable to find valid measurement date"
        raise AllotropyError(msg)

    def _get_device_control_aggregate_document(
        self, data: Data, plate: Plate
    ) -> DeviceControlAggregateDocument:
        ex_filter = data.labels.excitation_filter
        em_filter = data.labels.get_emission_filter(plate.plate_info.emission_filter_id)

        read_type = self._get_read_type(data)
        device_control_aggregate_document_class = READ_TYPE_TO_DEVICE_CONTROL_AGGREGATE_DOCUMENT[read_type]
        device_control_document_item_class = READ_TYPE_TO_MEASUREMENT_DOCUMENT_ITEMS[read_type]

        return device_control_aggregate_document_class(
            [
                device_control_document_item_class(
                    device_type="fluorescence detector",
                    detector_distance_setting__plate_reader_=safe_value(
                        TQuantityValueMillimeter, plate.plate_info.measured_height
                    ),
                    number_of_averages=safe_value(
                        TQuantityValueNumber, data.labels.number_of_flashes
                    ),
                    detector_gain_setting=data.labels.detector_gain_setting,
                    scan_position_setting__plate_reader_=data.labels.scan_position_setting,
                    detector_wavelength_setting=safe_value(
                        TQuantityValueNanometer,
                        em_filter.wavelength if em_filter else None,
                    ),
                    detector_bandwidth_setting=safe_value(
                        TQuantityValueNanometer,
                        em_filter.bandwidth if em_filter else None,
                    ),
                    excitation_wavelength_setting=safe_value(
                        TQuantityValueNanometer,
                        ex_filter.wavelength if ex_filter else None,
                    ),
                    excitation_bandwidth_setting=safe_value(
                        TQuantityValueNanometer,
                        ex_filter.bandwidth if ex_filter else None,
                    ),
                )
            ]
        )

    def _get_measurement_document(
        self,
        plate: Plate,
        result: Result,
        p_map: PlateMap,
        device_control_document: DeviceControlDocument,
    ) -> MeasurementDocumentItems:
        return FluorescencePointDetectionMeasurementDocumentItems(
            measurement_identifier=str(uuid.uuid4()),
            sample_document=SampleDocument(
                sample_identifier=str(
                    uuid.uuid4()
                ),  # TODO check what this should map to
                location_identifier=str(
                    uuid.uuid4()
                ),  # TODO check what this should map to
                well_plate_identifier=plate.plate_info.barcode,
                well_location_identifier=f"{result.col}{result.row}",
                sample_role_type=str(
                    p_map.get_sample_role_type(result.col, result.row)
                ),
            ),
            device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[device_control_document],
            ),
            fluorescence=TRelativeFluorescenceUnit(result.value),
            compartment_temperature=safe_value(
                TQuantityValueDegreeCelsius,
                plate.plate_info.chamber_temperature_at_start,
            ),
        )

    def _get_plate_reader_document(self, data: Data) -> list[PlateReaderDocumentItem]:
        items = []
        measurement_time = self._get_measurement_time(data)
        for plate in data.plates:
            if plate.results is None:
                continue

            try:
                p_map = data.plate_maps[plate.plate_info.number]
            except KeyError as e:
                msg = f"Unable to find plate map of {plate.plate_info.barcode}"
                raise AllotropyError(msg) from e

            device_control_aggregate_document = (
                self._get_device_control_aggregate_document(data, plate)
            )

            items += [
                PlateReaderDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_time=measurement_time,
                        plate_well_count=TQuantityValueNumber(
                            value=data.number_of_wells
                        ),
                        measurement_document=[
                            self._get_measurement_document(
                                plate, result, p_map, device_control_aggregate_document
                            )
                        ],
                        analytical_method_identifier=data.basic_assay_info.protocol_id,
                        experimental_data_identifier=data.basic_assay_info.assay_id,
                        container_type=ContainerType.well_plate,
                    )
                )
                for result in plate.results
            ]
        return items
