from __future__ import annotations

from collections import defaultdict

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.dpcr import (
    CalculatedDataDocumentItem,
    ContainerType,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    DPCRAggregateDocument,
    DPCRDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    TCalculatedDataAggregateDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueNumber,
    TQuantityValueNumberPerMicroliter,
)
from allotropy.allotrope.models.shared.definitions.definitions import TQuantityValue
from allotropy.allotrope.pandas_util import read_csv
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_structure import (
    Group,
    Well,
    WellItem,
)
from allotropy.parsers.appbio_absolute_q.constants import (
    BRAND_NAME,
    DEVICE_TYPE,
    PLATE_WELL_COUNT,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class AppbioAbsoluteQParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "AppBio AbsoluteQ"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        filename = named_file_contents.original_file_name
        data = read_csv(
            filepath_or_buffer=named_file_contents.contents, parse_dates=["Date"]
        )
        wells = Well.create_wells(data)
        groups = Group.create_rows(data)
        return self._get_model(wells, groups, filename)

    def _get_model(
        self, wells: list[Well], groups: list[Group], filename: str
    ) -> Model:
        # Map measurement ids to group keys
        group_to_ids = defaultdict(list)
        for well in wells:
            for item in well.items:
                group_to_ids[item.group_key].append(item.measurement_identifier)

        calculated_data_documents = [
            doc
            for group in groups
            for doc in self.get_calculated_data_documents(
                group, group_to_ids[group.key]
            )
        ]
        return Model(
            dPCR_aggregate_document=DPCRAggregateDocument(
                device_system_document=DeviceSystemDocument(
                    device_identifier=wells[0].items[0].instrument_identifier,
                    brand_name=BRAND_NAME,
                    product_manufacturer=PRODUCT_MANUFACTURER,
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name=SOFTWARE_NAME,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                dPCR_document=[
                    DPCRDocumentItem(
                        measurement_aggregate_document=MeasurementAggregateDocument(
                            experimental_data_identifier=well.items[0].run_identifier,
                            plate_well_count=TQuantityValueNumber(
                                value=PLATE_WELL_COUNT
                            ),
                            container_type=ContainerType.well_plate,
                            measurement_document=[
                                self._get_measurement_document(well_item)
                                for well_item in well.items
                            ],
                        )
                    )
                    for well in wells
                ],
                calculated_data_aggregate_document=TCalculatedDataAggregateDocument(
                    calculated_data_document=calculated_data_documents
                )
                if calculated_data_documents
                else None,
            )
        )

    def _get_measurement_document(self, well_item: WellItem) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            measurement_identifier=well_item.measurement_identifier,
            measurement_time=self._get_date_time(well_item.timestamp),
            target_DNA_description=well_item.target_identifier,
            total_partition_count=TQuantityValueNumber(
                value=well_item.total_partition_count
            ),
            sample_document=SampleDocument(
                sample_identifier=well_item.name,
                well_location_identifier=well_item.well_identifier,
                well_plate_identifier=well_item.plate_identifier,
            ),
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        device_type=DEVICE_TYPE,
                        reporter_dye_setting=well_item.reporter_dye_setting,
                    )
                ]
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    ProcessedDataDocumentItem(
                        number_concentration=TQuantityValueNumberPerMicroliter(
                            value=well_item.concentration
                        ),
                        positive_partition_count=TQuantityValueNumber(
                            value=well_item.positive_partition_count
                        ),
                    )
                ]
            ),
        )

    @staticmethod
    def get_calculated_data_documents(
        group: Group, source_ids: list[str]
    ) -> list[CalculatedDataDocumentItem]:
        # TODO: if aggregation type is Replicate(Average), check for required columns
        # Raise if column(s) do not exist
        return [
            CalculatedDataDocumentItem(
                calculated_data_identifier=calculated_data.identifier,
                data_source_aggregate_document=DataSourceAggregateDocument(
                    data_source_document=[
                        DataSourceDocumentItem(
                            data_source_identifier=source.identifier,
                            data_source_feature=source.feature,
                        )
                        for source in calculated_data.get_data_sources(
                            source_ids, group.calculated_data_ids
                        )
                    ]
                ),
                calculated_data_name=calculated_data.name,
                calculated_datum=TQuantityValue(
                    value=calculated_data.value, unit=calculated_data.unit
                ),
            )
            for calculated_data in group.calculated_data
        ]
