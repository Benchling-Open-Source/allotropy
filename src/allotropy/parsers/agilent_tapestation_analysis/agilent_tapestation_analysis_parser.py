# mypy: disallow_any_generics = False

from __future__ import annotations

from allotropy.allotrope.models.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataRegionAggregateDocument,
    DataRegionDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ElectrophoresisAggregateDocument,
    ElectrophoresisDocumentItem,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    PeakItem,
    PeakList,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    TQuantityValueModel,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValuePercent,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure import (
    Data,
    DataRegion,
    Metadata,
    Peak,
    Sample,
)
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    BRAND_NAME,
    DETECTION_TYPE,
    DEVICE_TYPE,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
    UNIT_CLASSES,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser


class AgilentTapestationAnalysisParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Agilent TapeStation Analysis"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = Data.create(named_file_contents.contents)
        filename = named_file_contents.original_file_name
        return self._get_model(filename, data)

    def _get_model(self, filename: str, data: Data) -> Model:
        metadata = data.metadata

        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/electrophoresis/BENCHLING/2024/06/electrophoresis.manifest",
            electrophoresis_aggregate_document=ElectrophoresisAggregateDocument(
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=metadata.data_system_instance_identifier,
                    file_name=filename,
                    software_name=SOFTWARE_NAME,
                    software_version=metadata.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                device_system_document=DeviceSystemDocument(
                    brand_name=BRAND_NAME,
                    product_manufacturer=PRODUCT_MANUFACTURER,
                    device_identifier=metadata.device_identifier,
                    equipment_serial_number=metadata.equipment_serial_number,
                ),
                electrophoresis_document=self._get_electrophoresis_document(
                    metadata, data.samples_list.samples
                ),
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(
                    data.samples_list.samples
                ),
            ),
        )

    def _get_electrophoresis_document(
        self, metadata: Metadata, samples: list[Sample]
    ) -> list[ElectrophoresisDocumentItem]:
        return [
            ElectrophoresisDocumentItem(
                measurement_aggregate_document=MeasurementAggregateDocument(
                    measurement_document=[
                        MeasurementDocumentItem(
                            measurement_identifier=sample.measurement_identifier,
                            measurement_time=self._get_date_time(
                                sample.measurement_time
                            ),
                            compartment_temperature=quantity_or_none(
                                TQuantityValueDegreeCelsius,
                                sample.compartment_temperature,
                            ),
                            device_control_aggregate_document=DeviceControlAggregateDocument(
                                device_control_document=[
                                    DeviceControlDocumentItem(
                                        device_type=DEVICE_TYPE,
                                        detection_type=DETECTION_TYPE,
                                    )
                                ]
                            ),
                            sample_document=SampleDocument(
                                sample_identifier=sample.sample_identifier,
                                description=sample.description,
                                location_identifier=sample.location_identifier,
                            ),
                            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                                processed_data_document=[
                                    ProcessedDataDocumentItem(
                                        peak_list=self._get_peak_list(
                                            sample.peak_list, metadata.unit_cls
                                        ),
                                        data_region_aggregate_document=self._get_data_region_aggregate_document(
                                            sample.data_regions,
                                            unit_cls=metadata.unit_cls,
                                        ),
                                    )
                                ]
                            ),
                            error_aggregate_document=(
                                ErrorAggregateDocument(
                                    error_document=(
                                        [ErrorDocumentItem(error=sample.error)]
                                    )
                                )
                                if sample.error
                                else None
                            ),
                        )
                    ]
                ),
                analyst=metadata.analyst,
                analytical_method_identifier=metadata.analytical_method_identifier,
                method_version=metadata.method_version,
                experimental_data_identifier=metadata.experimental_data_identifier,
            )
            for sample in samples
        ]

    def _get_peak_list(self, peaks: list[Peak], unit_cls: UNIT_CLASSES) -> PeakList:
        return PeakList(
            peak=[
                PeakItem(
                    peak_identifier=peak.peak_identifier,
                    peak_name=peak.peak_name,
                    peak_height=TQuantityValueRelativeFluorescenceUnit(
                        value=peak.peak_height
                    ),
                    peak_start=unit_cls(value=peak.peak_start),
                    peak_end=unit_cls(value=peak.peak_end),
                    peak_position=unit_cls(value=peak.peak_position),
                    peak_area=TQuantityValueUnitless(value=peak.peak_area),
                    relative_peak_area=TQuantityValuePercent(
                        value=peak.relative_peak_area
                    ),
                    relative_corrected_peak_area=TQuantityValuePercent(
                        value=peak.relative_corrected_peak_area
                    ),
                    comment=peak.comment,
                )
                for peak in peaks
            ]
        )

    def _get_data_region_aggregate_document(
        self, data_regions: list[DataRegion], unit_cls: UNIT_CLASSES
    ) -> DataRegionAggregateDocument | None:
        if not data_regions:
            return None

        return DataRegionAggregateDocument(
            data_region_document=[
                DataRegionDocumentItem(
                    region_identifier=data_region.region_identifier,
                    region_name=data_region.region_name,
                    region_start=unit_cls(value=data_region.region_start),
                    region_end=unit_cls(value=data_region.region_end),
                    region_area=TQuantityValueUnitless(value=data_region.region_area),
                    relative_region_area=TQuantityValuePercent(
                        value=data_region.relative_region_area
                    ),
                    comment=data_region.comment,
                )
                for data_region in data_regions
            ]
        )

    def _get_calculated_data_aggregate_document(
        self, samples: list[Sample]
    ) -> CalculatedDataAggregateDocument | None:
        calculated_data_document: list[CalculatedDataDocumentItem] = []
        for sample in samples:
            calculated_data_document.extend(
                self._get_calculated_data_document_items(sample.calculated_data)
            )
            for peak in sample.peak_list:
                calculated_data_document.extend(
                    self._get_calculated_data_document_items(peak.calculated_data)
                )
            for region in sample.data_regions:
                calculated_data_document.extend(
                    self._get_calculated_data_document_items(region.calculated_data)
                )

        return (
            CalculatedDataAggregateDocument(
                calculated_data_document=calculated_data_document
            )
            if calculated_data_document
            else None
        )

    def _get_calculated_data_document_items(
        self, calculated_data: list[CalculatedDocument]
    ) -> list[CalculatedDataDocumentItem]:
        return [
            CalculatedDataDocumentItem(
                calculated_data_identifier=calculated_document.uuid,
                calculated_data_name=calculated_document.name,
                calculated_result=TQuantityValueModel(
                    value=calculated_document.value, unit=UNITLESS
                ),
                data_source_aggregate_document=DataSourceAggregateDocument(
                    data_source_document=[
                        DataSourceDocumentItem(
                            data_source_identifier=source.reference.uuid,
                            data_source_feature=source.feature,
                        )
                        for source in calculated_document.data_sources
                    ]
                ),
            )
            for calculated_document in calculated_data
        ]
