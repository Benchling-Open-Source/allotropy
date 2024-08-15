import re
from typing import Any

from allotropy.allotrope.models.adm.light_obscuration.benchling._2023._12.light_obscuration import (
    CalculatedDataDocumentItem,
    DataProcessingDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceDocumentItem,
    DeviceSystemDocument,
    DistributionAggregateDocument,
    DistributionDocumentItem,
    DistributionItem,
    LightObscurationAggregateDocument,
    LightObscurationDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    TCalculatedDataAggregateDocument,
    TDataSourceAggregateDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCountsPerMilliliter,
    TQuantityValueMicrometer,
    TQuantityValueMilliliter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.allotrope.schema_mappers.adm.light_obscuration._2023._12.light_obscuration import (
    CalculatedDataItem,
    Data,
    ProcessedDataFeature,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_structure import (
    create_data,
    Distribution,
    PharmSpecData,
)
from allotropy.parsers.beckman_pharmspec.constants import PHARMSPEC_SOFTWARE_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.pandas import read_excel
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser


class PharmSpecParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Beckman PharmSpec"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = create_data(named_file_contents)
        return self._setup_model(data)

    def _create_distribution_document_items(
        self, features: list[ProcessedDataFeature]
    ) -> list[DistributionDocumentItem]:
        """Create the distribution document. First, we create the actual distribution, which itself
        contains a list of DistributionDocumentItem objects. The DistributionDocumentItem objects represent
        the values from the rows of the incoming dataframe.

        :param distribution: the Distribution object
        :return: The DistributionDocument
        """
        return [DistributionDocumentItem(distribution=[
            DistributionItem(
                distribution_identifier=feature.identifier,
                particle_size=TQuantityValueMicrometer(value=feature.particle_size),
                cumulative_count=TQuantityValueUnitless(value=feature.cumulative_count),
                cumulative_particle_density=TQuantityValueCountsPerMilliliter(value=feature.cumulative_particle_density),
                differential_particle_density=quantity_or_none(TQuantityValueCountsPerMilliliter, feature.differential_particle_density),
                differential_count=quantity_or_none(TQuantityValueUnitless, feature.differential_count),
            )
            for feature in features
        ])]

    def _create_measurement_document_items(
        self, data: Data
    ) -> list[MeasurementDocumentItem]:
        items = []
        for measurement in data.measurement_groups[0].measurements:
            items.append(
                MeasurementDocumentItem(
                    measurement_identifier=measurement.identifier,
                    measurement_time=self._get_date_time(measurement.measurement_time),
                    device_control_aggregate_document=DeviceControlAggregateDocument(
                        device_control_document=[
                            DeviceControlDocumentItem(
                                flush_volume_setting=TQuantityValueMilliliter(
                                    value=measurement.flush_volume_setting
                                ),
                                detector_view_volume=TQuantityValueMilliliter(
                                    value=measurement.detector_view_volume
                                ),
                                repetition_setting=measurement.repetition_setting,
                                sample_volume_setting=TQuantityValueMilliliter(
                                    value=measurement.sample_volume_setting,
                                ),
                            )
                        ]
                    ),
                    sample_document=SampleDocument(
                        sample_identifier=measurement.sample_identifier,
                    ),
                    processed_data_aggregate_document=ProcessedDataAggregateDocument(
                        processed_data_document=[
                            ProcessedDataDocumentItem(
                                data_processing_document=DataProcessingDocument(
                                    dilution_factor_setting=TQuantityValueUnitless(
                                        value=measurement.processed_data.dilution_factor_setting,
                                    )
                                ),
                                distribution_aggregate_document=DistributionAggregateDocument(
                                    distribution_document=self._create_distribution_document_items(
                                        measurement.processed_data.distributions
                                    )
                                ),
                            )
                        ]
                    ),
                )
            )

        return items

    def _create_model(self, data: Data) -> Model:
        measurement_doc_items = self._create_measurement_document_items(data)
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/light-obscuration/BENCHLING/2023/12/light-obscuration.manifest",
            light_obscuration_aggregate_document=LightObscurationAggregateDocument(
                light_obscuration_document=[
                    LightObscurationDocumentItem(
                        measurement_aggregate_document=MeasurementAggregateDocument(
                            analyst=measurement_group.analyst,
                            measurement_document=measurement_doc_items,
                        )
                    )
                    for measurement_group in data.measurement_groups
                ],
                data_system_document=DataSystemDocument(
                    file_name=data.metadata.file_name,
                    software_name=data.metadata.software_name,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                device_system_document=DeviceSystemDocument(
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    device_document=[
                        DeviceDocumentItem(
                            detector_identifier=data.metadata.detector_identifier,
                            detector_model_number=data.metadata.detector_model_number,
                        )
                    ],
                ),
                calculated_data_aggregate_document=self._get_calculated_data_aggregate_document(data.calculated_data),
            ),
        )

    def _setup_model(self, data: Data) -> Model:
        """Build the Model

        :param df: the raw dataframe
        :return: the model
        """
        return self._create_model(data)

    def _get_calculated_data_aggregate_document(
        self, calculated_data_items: list[CalculatedDataItem] | None
    ) -> TCalculatedDataAggregateDocument | None:
        if not calculated_data_items:
            return None

        return TCalculatedDataAggregateDocument(
            calculated_data_document=[
                CalculatedDataDocumentItem(
                    calculated_data_identifier=calculated_data_item.identifier,
                    calculated_data_name=calculated_data_item.name,
                    calculated_result=TQuantityValue(
                        value=calculated_data_item.value,
                        unit=calculated_data_item.unit,
                    ),
                    data_source_aggregate_document=TDataSourceAggregateDocument(
                        data_source_document=[
                            DataSourceDocumentItem(
                                data_source_identifier=item.identifier,
                                data_source_feature=item.feature,
                            )
                            for item in calculated_data_item.data_sources
                        ]
                    ),
                )
                for calculated_data_item in calculated_data_items
            ]
        )
