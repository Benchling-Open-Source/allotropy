# mypy: disallow_any_generics = False

from __future__ import annotations

from allotropy.allotrope.models.adm.electrophoresis.benchling._2024._06.electrophoresis import (
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
from allotropy.allotrope.schema_mappers.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    CalculatedDataItem,
    Data,
    MeasurementGroup,
    Metadata,
    ProcessedDataFeature,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure import (
    create_data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.units import get_quantity_class
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
        data = create_data(named_file_contents)
        return self._get_model(data)

    def _get_model(self, data: Data) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/electrophoresis/BENCHLING/2024/06/electrophoresis.manifest",
            electrophoresis_aggregate_document=ElectrophoresisAggregateDocument(
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier=data.metadata.data_system_instance_identifier,
                    file_name=data.metadata.file_name,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                device_system_document=DeviceSystemDocument(
                    brand_name=data.metadata.brand_name,
                    product_manufacturer=data.metadata.product_manufacturer,
                    device_identifier=data.metadata.device_identifier,
                    equipment_serial_number=data.metadata.equipment_serial_number,
                ),
                electrophoresis_document=self._get_electrophoresis_document(
                    data.metadata, data.measurement_groups
                ),
                calculated_data_aggregate_document=self._get_calculated_data_document_items(
                    data.calculated_data
                ),
            ),
        )

    def _get_electrophoresis_document(
        self, metadata: Metadata, measurement_groups: list[MeasurementGroup]
    ) -> list[ElectrophoresisDocumentItem]:
        return [
            ElectrophoresisDocumentItem(
                measurement_aggregate_document=MeasurementAggregateDocument(
                    measurement_document=[
                        MeasurementDocumentItem(
                            measurement_identifier=measurement_group.measurements[0].identifier,
                            measurement_time=self._get_date_time(
                                measurement_group.measurements[0].measurement_time
                            ),
                            compartment_temperature=quantity_or_none(
                                TQuantityValueDegreeCelsius,
                                measurement_group.measurements[0].compartment_temperature,
                            ),
                            device_control_aggregate_document=DeviceControlAggregateDocument(
                                device_control_document=[
                                    DeviceControlDocumentItem(
                                        device_type=metadata.device_type,
                                        detection_type=metadata.detection_type,
                                    )
                                ]
                            ),
                            sample_document=SampleDocument(
                                sample_identifier=measurement_group.measurements[0].sample_identifier,
                                description=measurement_group.measurements[0].description,
                                location_identifier=measurement_group.measurements[0].location_identifier,
                            ),
                            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                                processed_data_document=[
                                    ProcessedDataDocumentItem(
                                        peak_list=self._get_peak_list(
                                            measurement_group.measurements[0].processed_data.peaks,
                                        ),
                                        data_region_aggregate_document=self._get_data_region_aggregate_document(
                                            measurement_group.measurements[0].processed_data.data_regions,
                                        ),
                                    )
                                ]
                            ),
                            error_aggregate_document=(
                                ErrorAggregateDocument(
                                    error_document=(
                                        [ErrorDocumentItem(error=measurement_group.measurements[0].errors[0].error)]
                                    )
                                )
                                if measurement_group.measurements[0].errors
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
            for measurement_group in measurement_groups
        ]

    def _get_peak_list(self, peaks: list[ProcessedDataFeature]) -> PeakList:
        return PeakList(
            peak=[
                PeakItem(
                    peak_identifier=peak.identifier,
                    peak_name=peak.name,
                    peak_height=TQuantityValueRelativeFluorescenceUnit(
                        value=peak.height
                    ),
                    peak_start=get_quantity_class(peak.start_unit)(value=peak.start),
                    peak_end=get_quantity_class(peak.end_unit)(value=peak.end),
                    peak_position=get_quantity_class(peak.position_unit)(value=peak.position),
                    peak_area=TQuantityValueUnitless(value=peak.area),
                    relative_peak_area=TQuantityValuePercent(
                        value=peak.relative_area
                    ),
                    relative_corrected_peak_area=TQuantityValuePercent(
                        value=peak.relative_corrected_area
                    ),
                    comment=peak.comment,
                )
                for peak in peaks
            ]
        )

    def _get_data_region_aggregate_document(self, data_regions: list[ProcessedDataFeature]) -> DataRegionAggregateDocument | None:
        if not data_regions:
            return None

        return DataRegionAggregateDocument(
            data_region_document=[
                DataRegionDocumentItem(
                    region_identifier=data_region.identifier,
                    region_name=data_region.name,
                    region_start=get_quantity_class(data_region.start_unit)(value=data_region.start),
                    region_end=get_quantity_class(data_region.end_unit)(value=data_region.end),
                    region_area=TQuantityValueUnitless(value=data_region.area),
                    relative_region_area=TQuantityValuePercent(
                        value=data_region.relative_area
                    ),
                    comment=data_region.comment,
                )
                for data_region in data_regions
            ]
        )

    def _get_calculated_data_document_items(
        self, calculated_data: list[CalculatedDataItem]
    ) -> list[CalculatedDataDocumentItem]:
        return [
            CalculatedDataDocumentItem(
                calculated_data_identifier=calculated_document.identifier,
                calculated_data_name=calculated_document.name,
                calculated_result=TQuantityValueModel(
                    value=calculated_document.value, unit=calculated_document.unit
                ),
                data_source_aggregate_document=DataSourceAggregateDocument(
                    data_source_document=[
                        DataSourceDocumentItem(
                            data_source_identifier=source.identifier,
                            data_source_feature=source.feature,
                        )
                        for source in calculated_document.data_sources
                    ]
                ),
            )
            for calculated_document in calculated_data
        ]
