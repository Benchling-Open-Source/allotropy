# mypy: disallow_any_generics = False

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

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
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_reader import AbsoluteQReader
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_structure import (
    GroupRow,
    Well,
    WellItem,
)
from allotropy.parsers.appbio_absolute_q.constants import (
    BRAND_NAME,
    CALCULATED_DATA_REFERENCE,
    CalculatedDataSource,
    DEVICE_TYPE,
    PLATE_WELL_COUNT,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class AppbioAbsoluteQParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "AppBio AbsoluteQ"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        raw_contents = named_file_contents.contents
        filename = named_file_contents.original_file_name
        reader = AbsoluteQReader(raw_contents)
        return self._get_model(reader.wells, reader.group_rows, filename)

    def _get_model(
        self, well_data: pd.DataFrame, group_rows: pd.DataFrame, filename: str
    ) -> Model:
        group_ids: dict[Any, list] = defaultdict(list)
        wells = Well.create_wells(well_data)

        dpcr_document = [
            DPCRDocumentItem(
                measurement_aggregate_document=MeasurementAggregateDocument(
                    experimental_data_identifier=well.items[0].run_identifier,
                    plate_well_count=TQuantityValueNumber(value=PLATE_WELL_COUNT),
                    container_type=ContainerType.well_plate,
                    measurement_document=[
                        self._get_measurement_document(well_item, group_ids)
                        for well_item in well.items
                    ],
                )
            )
            for well in wells
        ]

        calculated_data_aggregate_document = None
        calculated_data_document = self.get_calculated_data_document(
            group_ids, group_rows
        )

        if calculated_data_document:
            calculated_data_aggregate_document = TCalculatedDataAggregateDocument(
                calculated_data_document=calculated_data_document
            )

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
                dPCR_document=dpcr_document,
                calculated_data_aggregate_document=calculated_data_aggregate_document,
            )
        )

    def _get_measurement_document(
        self, well_item: WellItem, group_ids: dict[Any, list]
    ) -> MeasurementDocumentItem:
        measurement_identifier = random_uuid_str()

        key = str((well_item.group_identifier, well_item.target_identifier))
        group_ids[key].append(measurement_identifier)

        return MeasurementDocumentItem(
            measurement_identifier=measurement_identifier,
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
    def get_calculated_data_document(
        group_ids: dict, group_rows_data: pd.DataFrame
    ) -> list[CalculatedDataDocumentItem]:
        calculated_data_document: list[CalculatedDataDocumentItem] = []
        group_rows = GroupRow.create_rows(group_rows_data)

        for group in group_rows:
            # Samples designated as "Individual" include no calculated data
            if group.aggregation_type not in CALCULATED_DATA_REFERENCE:
                continue

            key = str((group.name, group.target_identifier))

            ids = group_ids[key]
            calculated_data_ids: dict[str, str] = {}

            for calculated_data_item in sorted(
                CALCULATED_DATA_REFERENCE[group.aggregation_type],
                key=lambda item: item.source == CalculatedDataSource.CALCULATED_DATA,
            ):
                # TODO: if aggregation type is Replicate(Average), check for required columns
                # Raise if column(s) do not exist

                # Calculated data items that have another calculated data as data source
                # need to be created after the later
                data_source_identifiers = []
                if calculated_data_item.source == CalculatedDataSource.CALCULATED_DATA:
                    data_source_identifiers = [
                        (calculated_data_ids[source_feature], source_feature)
                        for source_feature in calculated_data_item.source_features
                    ]
                else:
                    data_source_identifiers = [
                        (identifier, calculated_data_item.source_feature)
                        for identifier in ids
                    ]

                datum_value = float(group.data[calculated_data_item.column])
                calculated_data_id = random_uuid_str()
                calculated_data_ids[calculated_data_item.name] = calculated_data_id

                data_source_document = [
                    DataSourceDocumentItem(
                        data_source_identifier=identifier,
                        data_source_feature=source_feature,
                    )
                    for identifier, source_feature in data_source_identifiers
                ]
                calculated_data_document.append(
                    CalculatedDataDocumentItem(
                        calculated_data_identifier=calculated_data_id,
                        data_source_aggregate_document=DataSourceAggregateDocument(
                            data_source_document=data_source_document
                        ),
                        calculated_data_name=calculated_data_item.name,
                        calculated_datum=TQuantityValue(
                            value=datum_value,
                            unit=calculated_data_item.unit,
                        ),
                    )
                )

        return calculated_data_document
