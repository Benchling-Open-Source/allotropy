from collections import defaultdict
from enum import Enum
from typing import cast

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    ContainerType,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlDocument,
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
    TQuantityValueDegreeCelsius,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueMillimeter,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueRelativeLightUnit,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TDateTimeValue,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_structure import (
    CalculatedPlateInfo,
    Data,
    Plate,
    PlateMap,
    Result,
    ResultPlateInfo,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser


class ReadType(Enum):
    ABSORBANCE = "Absorbance"
    FLUORESCENCE = "Fluorescence"
    LUMINESCENCE = "Luminescence"


MeasurementDocumentItems = (
    OpticalImagingMeasurementDocumentItems
    | UltravioletAbsorbancePointDetectionMeasurementDocumentItems
    | FluorescencePointDetectionMeasurementDocumentItems
    | LuminescencePointDetectionMeasurementDocumentItems
)


DeviceControlAggregateDocument = (
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument
    | FluorescencePointDetectionDeviceControlAggregateDocument
    | LuminescencePointDetectionDeviceControlAggregateDocument
)


class PerkinElmerEnvisionParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "PerkinElmer Envision"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        filename = named_file_contents.original_file_name
        return self._get_model(Data.create(reader), filename)

    def _get_model(self, data: Data, filename: str) -> Model:
        if data.number_of_wells is None:
            msg = "Unable to determine the number of wells in the plate."
            raise AllotropeConversionError(msg)

        read_type = self._get_read_type(data)

        return Model(
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                plate_reader_document=self._get_plate_reader_document(data, read_type),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=data.software.software_name,
                    software_version=data.software.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                device_system_document=DeviceSystemDocument(
                    model_number="EnVision",
                    equipment_serial_number=data.instrument.serial_number,
                    device_identifier=data.instrument.nickname,
                ),
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data, read_type
                ),
            ),
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
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

        return (
            ReadType.FLUORESCENCE
        )  # TODO check if this is correct, this is the original behavior

    def _get_measurement_time(self, data: Data) -> TDateTimeValue:
        dates = [
            plate.plate_info.measurement_time
            for plate in data.plate_list.plates
            if plate.plate_info.measurement_time
        ]

        if dates:
            return self._get_date_time(min(dates))

        msg = "Unable to determine the measurement time."
        raise AllotropeConversionError(msg)

    def _get_device_control_aggregate_document(
        self,
        data: Data,
        result_plate_info: ResultPlateInfo,
        read_type: ReadType,
    ) -> DeviceControlAggregateDocument:
        ex_filter = data.labels.excitation_filter
        em_filter = data.labels.get_emission_filter(
            result_plate_info.emission_filter_id
        )

        if read_type == ReadType.LUMINESCENCE:
            return LuminescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    LuminescencePointDetectionDeviceControlDocumentItem(
                        device_type="luminescence detector",
                        detector_distance_setting__plate_reader_=quantity_or_none(
                            TQuantityValueMillimeter, result_plate_info.measured_height
                        ),
                        number_of_averages=quantity_or_none(
                            TQuantityValueNumber, data.labels.number_of_flashes
                        ),
                        detector_gain_setting=data.labels.detector_gain_setting,
                        scan_position_setting__plate_reader_=data.labels.scan_position_setting,
                        detector_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            em_filter.wavelength if em_filter else None,
                        ),
                        detector_bandwidth_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            em_filter.bandwidth if em_filter else None,
                        ),
                    )
                ]
            )
        elif read_type == ReadType.ABSORBANCE:
            return UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                        device_type="absorbance detector",
                        detector_distance_setting__plate_reader_=quantity_or_none(
                            TQuantityValueMillimeter, result_plate_info.measured_height
                        ),
                        number_of_averages=quantity_or_none(
                            TQuantityValueNumber, data.labels.number_of_flashes
                        ),
                        detector_gain_setting=data.labels.detector_gain_setting,
                        scan_position_setting__plate_reader_=data.labels.scan_position_setting,
                        detector_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            em_filter.wavelength if em_filter else None,
                        ),
                        detector_bandwidth_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            em_filter.bandwidth if em_filter else None,
                        ),
                    )
                ]
            )
        else:  # read_type is FLUORESCENCE
            return FluorescencePointDetectionDeviceControlAggregateDocument(
                device_control_document=[
                    FluorescencePointDetectionDeviceControlDocumentItem(
                        device_type="fluorescence detector",
                        detector_distance_setting__plate_reader_=quantity_or_none(
                            TQuantityValueMillimeter, result_plate_info.measured_height
                        ),
                        number_of_averages=quantity_or_none(
                            TQuantityValueNumber, data.labels.number_of_flashes
                        ),
                        detector_gain_setting=data.labels.detector_gain_setting,
                        scan_position_setting__plate_reader_=data.labels.scan_position_setting,
                        detector_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            em_filter.wavelength if em_filter else None,
                        ),
                        detector_bandwidth_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            em_filter.bandwidth if em_filter else None,
                        ),
                        excitation_wavelength_setting=quantity_or_none(
                            TQuantityValueNanometer,
                            ex_filter.wavelength if ex_filter else None,
                        ),
                        excitation_bandwidth_setting=quantity_or_none(
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
        device_control_document: list[DeviceControlDocument],
        read_type: ReadType,
    ) -> MeasurementDocumentItems:
        plate_barcode = plate.plate_info.barcode
        well_location = f"{result.col}{result.row}"
        sample_document = SampleDocument(
            sample_identifier=f"{plate_barcode} {well_location}",
            well_plate_identifier=plate_barcode,
            location_identifier=well_location,
            sample_role_type=p_map.get_sample_role_type(result.col, result.row).value,
        )
        compartment_temperature = quantity_or_none(
            TQuantityValueDegreeCelsius,
            plate.plate_info.chamber_temperature_at_start,
        )
        if read_type == ReadType.ABSORBANCE:
            return UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
                measurement_identifier=result.uuid,
                sample_document=sample_document,
                device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                    device_control_document=cast(
                        list[
                            UltravioletAbsorbancePointDetectionDeviceControlDocumentItem
                        ],
                        device_control_document,
                    ),
                ),
                absorbance=TQuantityValueMilliAbsorbanceUnit(value=result.value),
                compartment_temperature=compartment_temperature,
            )
        elif read_type == ReadType.LUMINESCENCE:
            return LuminescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=result.uuid,
                sample_document=sample_document,
                device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=cast(
                        list[LuminescencePointDetectionDeviceControlDocumentItem],
                        device_control_document,
                    ),
                ),
                luminescence=TQuantityValueRelativeLightUnit(value=result.value),
                compartment_temperature=compartment_temperature,
            )
        else:  # read_type is FLUORESCENCE
            return FluorescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=result.uuid,
                sample_document=sample_document,
                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=cast(
                        list[FluorescencePointDetectionDeviceControlDocumentItem],
                        device_control_document,
                    ),
                ),
                fluorescence=TQuantityValueRelativeFluorescenceUnit(value=result.value),
                compartment_temperature=compartment_temperature,
            )

    def _get_plate_reader_document(
        self,
        data: Data,
        read_type: ReadType,
    ) -> list[PlateReaderDocumentItem]:
        items = []
        measurement_time = self._get_measurement_time(data)
        measurement_docs_dict = defaultdict(list)

        for plate in data.plate_list.plates:
            if isinstance(plate.plate_info, CalculatedPlateInfo):
                continue

            try:
                p_map = data.plate_maps[plate.plate_info.number]
            except KeyError as e:
                msg = f"Unable to find plate map for Plate {plate.plate_info.barcode}."
                raise AllotropeConversionError(msg) from e

            device_control_aggregate_document = (
                self._get_device_control_aggregate_document(
                    data, plate.plate_info, read_type
                )
            )

            for result in plate.result_list.results:
                measurement_docs_dict[
                    (plate.plate_info.number, result.col, result.row)
                ].append(
                    self._get_measurement_document(
                        plate,
                        result,
                        p_map,
                        cast(
                            list[DeviceControlDocument],
                            device_control_aggregate_document.device_control_document,
                        ),
                        read_type,
                    )
                )

        for well_location in sorted(measurement_docs_dict.keys()):
            items.append(
                PlateReaderDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_time=measurement_time,
                        plate_well_count=TQuantityValueNumber(
                            value=data.number_of_wells
                        ),
                        measurement_document=measurement_docs_dict[well_location],
                        analytical_method_identifier=data.basic_assay_info.protocol_id,
                        experimental_data_identifier=data.basic_assay_info.assay_id,
                        container_type=ContainerType.well_plate,
                    )
                )
            )

        return items

    def _get_calculated_data_aggregate_document(
        self,
        data: Data,
        read_type: ReadType,
    ) -> CalculatedDataAggregateDocument | None:
        calculated_documents = []

        for calculated_plate in data.plate_list.plates:
            if isinstance(calculated_plate.plate_info, ResultPlateInfo):
                continue

            source_result_lists = [
                source_plate.result_list.results
                for source_plate in calculated_plate.collect_result_plates(
                    data.plate_list
                )
            ]

            for calculated_result, *source_results in zip(
                calculated_plate.calculated_result_list.calculated_results,
                *source_result_lists,
                strict=True,
            ):
                calculated_documents.append(
                    CalculatedDataDocumentItem(
                        calculated_data_identifier=calculated_result.uuid,
                        calculated_data_name=calculated_plate.plate_info.name,
                        calculation_description=calculated_plate.plate_info.formula,
                        calculated_result=TQuantityValueUnitless(
                            value=calculated_result.value
                        ),
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier=source_result.uuid,
                                    data_source_feature=read_type.value,
                                )
                                for source_result in source_results
                            ]
                        ),
                    )
                )

        if not calculated_documents:
            return None

        return CalculatedDataAggregateDocument(
            calculated_data_document=calculated_documents,
        )
