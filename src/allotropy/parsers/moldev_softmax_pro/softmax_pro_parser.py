from collections.abc import Sequence
from itertools import chain

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    ContainerType,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
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
    ScanPositionSettingPlateReader,
    UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument,
    UltravioletAbsorbancePointDetectionDeviceControlDocumentItem,
    UltravioletAbsorbancePointDetectionMeasurementDocumentItems,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueRelativeLightUnit,
)
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import (
    AllotropeConversionError,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.moldev_softmax_pro.constants import (
    DEVICE_TYPE,
    EPOCH,
    REDUCED,
)
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import (
    Data,
    GroupBlock,
    GroupSampleData,
    PlateBlock,
    ScanPosition,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    quantity_or_none,
    try_nan_float_or_none,
)
from allotropy.parsers.vendor_parser import VendorParser

MeasurementDocumentItems = (
    OpticalImagingMeasurementDocumentItems
    | UltravioletAbsorbancePointDetectionMeasurementDocumentItems
    | FluorescencePointDetectionMeasurementDocumentItems
    | LuminescencePointDetectionMeasurementDocumentItems
)


class SoftmaxproParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Molecular Devices SoftMax Pro"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = Data.create(reader)
        return self._get_model(named_file_contents.original_file_name, data)

    def _get_model(self, file_name: str, data: Data) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/plate-reader/BENCHLING/2023/09/plate-reader.manifest",
            plate_reader_aggregate_document=PlateReaderAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=NOT_APPLICABLE,
                    model_number=NOT_APPLICABLE,
                ),
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    software_name="SoftMax Pro",
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                plate_reader_document=[
                    self._get_plate_reader_document_item(plate_block, position)
                    for plate_block in data.block_list.plate_blocks.values()
                    for position in plate_block.iter_wells()
                ],
                calculated_data_aggregate_document=self._get_calc_docs(data),
            ),
        )

    def _get_plate_reader_document_item(
        self, plate_block: PlateBlock, position: str
    ) -> PlateReaderDocumentItem:
        plate_block_type = plate_block.get_plate_block_type()

        measurement_document: Sequence[MeasurementDocumentItems]

        if plate_block_type == "Absorbance":
            measurement_document = self._get_absorbance_measurement_document(
                plate_block,
                position,
            )
        elif plate_block_type == "Luminescence":
            measurement_document = self._get_luminescence_measurement_document(
                plate_block,
                position,
            )
        elif plate_block_type == "Fluorescence":
            measurement_document = self._get_fluorescence_measurement_document(
                plate_block,
                position,
            )
        else:
            error = f"{plate_block_type} is not a valid plate block type."
            raise AllotropeConversionError(error)

        return PlateReaderDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=EPOCH,
                plate_well_count=TQuantityValueNumber(
                    value=plate_block.header.num_wells
                ),
                container_type=ContainerType.well_plate,
                measurement_document=list(measurement_document),
            )
        )

    def _get_fluorescence_measurement_document(
        self, plate_block: PlateBlock, position: str
    ) -> list[FluorescencePointDetectionMeasurementDocumentItems]:
        return [
            FluorescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=data_element.uuid,
                fluorescence=TQuantityValueRelativeFluorescenceUnit(
                    value=data_element.value
                ),
                compartment_temperature=quantity_or_none(
                    TQuantityValueDegreeCelsius,
                    try_nan_float_or_none(data_element.temperature),
                ),
                sample_document=SampleDocument(
                    location_identifier=data_element.position,
                    well_plate_identifier=plate_block.header.name,
                    sample_identifier=data_element.sample_identifier,
                ),
                device_control_aggregate_document=FluorescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        FluorescencePointDetectionDeviceControlDocumentItem(
                            device_type=DEVICE_TYPE,
                            detection_type=plate_block.header.read_mode,
                            scan_position_setting__plate_reader_=(
                                ScanPositionSettingPlateReader.top_scan_position__plate_reader_
                                if plate_block.header.scan_position == ScanPosition.TOP
                                else ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_
                            ),
                            detector_wavelength_setting=TQuantityValueNanometer(
                                value=data_element.wavelength
                            ),
                            excitation_wavelength_setting=quantity_or_none(
                                TQuantityValueNanometer,
                                plate_block.header.excitation_wavelengths,
                                index=idx,
                            ),
                            wavelength_filter_cutoff_setting=quantity_or_none(
                                TQuantityValueNanometer,
                                plate_block.header.cutoff_filters,
                                index=idx,
                            ),
                            number_of_averages=TQuantityValueNumber(
                                value=plate_block.header.reads_per_well
                            ),
                            detector_gain_setting=plate_block.header.pmt_gain,
                        )
                    ]
                ),
            )
            for idx, data_element in enumerate(plate_block.iter_data_elements(position))
        ]

    def _get_luminescence_measurement_document(
        self, plate_block: PlateBlock, position: str
    ) -> list[LuminescencePointDetectionMeasurementDocumentItems]:
        reads_per_well = assert_not_none(
            plate_block.header.reads_per_well,
            msg="Unable to find plate block reads per well.",
        )

        return [
            LuminescencePointDetectionMeasurementDocumentItems(
                measurement_identifier=data_element.uuid,
                luminescence=TQuantityValueRelativeLightUnit(value=data_element.value),
                compartment_temperature=quantity_or_none(
                    TQuantityValueDegreeCelsius,
                    try_nan_float_or_none(data_element.temperature),
                ),
                sample_document=SampleDocument(
                    location_identifier=data_element.position,
                    well_plate_identifier=plate_block.header.name,
                    sample_identifier=data_element.sample_identifier,
                ),
                device_control_aggregate_document=LuminescencePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        LuminescencePointDetectionDeviceControlDocumentItem(
                            device_type=DEVICE_TYPE,
                            detection_type=plate_block.header.read_mode,
                            detector_wavelength_setting=TQuantityValueNanometer(
                                value=data_element.wavelength
                            ),
                            number_of_averages=TQuantityValueNumber(
                                value=reads_per_well
                            ),
                            detector_gain_setting=plate_block.header.pmt_gain,
                        )
                    ]
                ),
            )
            for data_element in plate_block.iter_data_elements(position)
        ]

    def _get_absorbance_measurement_document(
        self, plate_block: PlateBlock, position: str
    ) -> list[UltravioletAbsorbancePointDetectionMeasurementDocumentItems]:
        return [
            UltravioletAbsorbancePointDetectionMeasurementDocumentItems(
                measurement_identifier=data_element.uuid,
                absorbance=TQuantityValueMilliAbsorbanceUnit(value=data_element.value),
                compartment_temperature=quantity_or_none(
                    TQuantityValueDegreeCelsius,
                    try_nan_float_or_none(data_element.temperature),
                ),
                sample_document=SampleDocument(
                    location_identifier=data_element.position,
                    well_plate_identifier=plate_block.header.name,
                    sample_identifier=data_element.sample_identifier,
                ),
                device_control_aggregate_document=UltravioletAbsorbancePointDetectionDeviceControlAggregateDocument(
                    device_control_document=[
                        UltravioletAbsorbancePointDetectionDeviceControlDocumentItem(
                            device_type=DEVICE_TYPE,
                            detection_type=plate_block.header.read_mode,
                            detector_wavelength_setting=TQuantityValueNanometer(
                                value=data_element.wavelength
                            ),
                        )
                    ]
                ),
            )
            for data_element in plate_block.iter_data_elements(position)
        ]

    def _get_calc_docs(self, data: Data) -> CalculatedDataAggregateDocument | None:
        calc_docs = self._get_reduced_calc_docs(data) + self._get_group_calc_docs(data)
        return (
            CalculatedDataAggregateDocument(calculated_data_document=calc_docs)
            if calc_docs
            else None
        )

    def _get_calc_docs_data_sources(
        self, plate_block: PlateBlock, position: str
    ) -> list[DataSourceDocumentItem]:
        return [
            DataSourceDocumentItem(
                data_source_identifier=data_source.uuid,
                data_source_feature=plate_block.get_plate_block_type(),
            )
            for data_source in plate_block.iter_data_elements(position)
        ]

    def _build_calc_doc(
        self,
        name: str,
        value: float,
        data_sources: list[DataSourceDocumentItem],
        description: str | None = None,
    ) -> CalculatedDataDocumentItem:
        return CalculatedDataDocumentItem(
            calculated_data_identifier=random_uuid_str(),
            calculated_data_name=name,
            calculation_description=description,
            calculated_result=TQuantityValue(unit=UNITLESS, value=value),
            data_source_aggregate_document=DataSourceAggregateDocument(
                data_source_document=data_sources
            ),
        )

    def _get_reduced_calc_docs(self, data: Data) -> list[CalculatedDataDocumentItem]:
        return [
            self._build_calc_doc(
                name=REDUCED,
                value=reduced_data_element.value,
                data_sources=self._get_calc_docs_data_sources(
                    plate_block,
                    reduced_data_element.position,
                ),
            )
            for plate_block in data.block_list.plate_blocks.values()
            for reduced_data_element in plate_block.iter_reduced_data()
        ]

    def _get_group_agg_calc_docs(
        self, data: Data, group_block: GroupBlock, group_sample_data: GroupSampleData
    ) -> list[CalculatedDataDocumentItem]:
        return [
            self._build_calc_doc(
                name=aggregated_entry.name,
                value=aggregated_entry.value,
                data_sources=list(
                    chain.from_iterable(
                        self._get_calc_docs_data_sources(
                            data.block_list.plate_blocks[group_data_element.plate],
                            group_data_element.position,
                        )
                        for group_data_element in group_sample_data.data_elements
                    )
                ),
                description=group_block.group_columns.data.get(aggregated_entry.name),
            )
            for aggregated_entry in group_sample_data.aggregated_entries
        ]

    def _get_group_simple_calc_docs(
        self, data: Data, group_block: GroupBlock, group_sample_data: GroupSampleData
    ) -> list[CalculatedDataDocumentItem]:
        calculated_documents = []
        for group_data_element in group_sample_data.data_elements:
            data_sources = self._get_calc_docs_data_sources(
                data.block_list.plate_blocks[group_data_element.plate],
                group_data_element.position,
            )
            for entry in group_data_element.entries:
                calculated_documents.append(
                    self._build_calc_doc(
                        name=entry.name,
                        value=entry.value,
                        data_sources=data_sources,
                        description=group_block.group_columns.data.get(entry.name),
                    )
                )
        return calculated_documents

    def _get_group_calc_docs(self, data: Data) -> list[CalculatedDataDocumentItem]:
        calculated_documents = []
        for group_block in data.block_list.group_blocks:
            for group_sample_data in group_block.group_data.sample_data:
                calculated_documents += self._get_group_agg_calc_docs(
                    data, group_block, group_sample_data
                )
                calculated_documents += self._get_group_simple_calc_docs(
                    data, group_block, group_sample_data
                )
        return calculated_documents
