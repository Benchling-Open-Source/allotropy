# mypy: disallow_any_generics = False

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from allotropy.allotrope.models.pcr_benchling_2023_09_dpcr import (
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
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_reader import AbsoluteQReader
from allotropy.parsers.appbio_absolute_q.constants import (
    AGGREGATION_LOOKUP,
    CALCULATED_DATA_REFERENCE,
    CalculatedDataItem,
    CalculatedDataSource,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser


class AppbioAbsoluteQParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        raw_contents = named_file_contents.contents
        filename = named_file_contents.original_file_name
        reader = AbsoluteQReader(raw_contents)
        return self._get_model(reader.wells, reader.group_rows, filename)

    def _get_model(
        self, wells: pd.DataFrame, group_rows: pd.DataFrame, filename: str
    ) -> Model:
        well_groups = wells.groupby(["Well"]).groups.keys()
        group_ids: dict[Any, list] = defaultdict(list)

        dpcr_document = [
            self._get_dpcr_document(wells[wells["Well"] == well_name], group_ids)
            for well_name in well_groups
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
                    device_identifier=wells.iloc[0]["Instrument"],
                    brand_name="QuantStudio Absolute Q Digital PCR System",
                    product_manufacturer="ThermoFisher Scientific",
                ),
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    software_name="QuantStudio Absolute Q Digital PCR Software",
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                dPCR_document=dpcr_document,
                calculated_data_aggregate_document=calculated_data_aggregate_document,
            )
        )

    def _get_dpcr_document(
        self, well_data: pd.DataFrame, group_ids: dict[Any, list]
    ) -> DPCRDocumentItem:
        measurement_documents = []
        for _, well_item in well_data.iterrows():
            measurement_identifier = random_uuid_str()

            key = str((well_item["Group"], well_item["Target"]))
            group_ids[key].append(measurement_identifier)

            measurement_documents.append(
                MeasurementDocumentItem(
                    measurement_identifier=measurement_identifier,
                    measurement_time=self._get_date_time(str(well_item["Date"])),
                    target_DNA_description=well_item["Target"],
                    total_partition_count=TQuantityValueNumber(
                        value=well_item["Total"]
                    ),
                    sample_document=SampleDocument(
                        sample_identifier=well_item["Name"],
                        well_location_identifier=well_item["Well"],
                        well_plate_identifier=well_item["Plate"],
                    ),
                    device_control_aggregate_document=DeviceControlAggregateDocument(
                        device_control_document=[
                            DeviceControlDocumentItem(
                                device_type="dPCR",
                                reporter_dye_setting=well_item["Dye"],
                            )
                        ]
                    ),
                    processed_data_aggregate_document=ProcessedDataAggregateDocument(
                        processed_data_document=[
                            ProcessedDataDocumentItem(
                                number_concentration=TQuantityValueNumberPerMicroliter(
                                    value=well_item["Conc. cp/uL"]
                                ),
                                positive_partition_count=TQuantityValueNumber(
                                    value=well_item["Positives"]
                                ),
                            )
                        ]
                    ),
                )
            )
        return DPCRDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                experimental_data_identifier=well_data.iloc[0]["Run"],
                plate_well_count=TQuantityValueNumber(value=16),
                container_type=ContainerType.well_plate,
                measurement_document=measurement_documents,
            )
        )

    @staticmethod
    def get_calculated_data_document(
        group_ids: dict, group_rows: pd.DataFrame
    ) -> list[CalculatedDataDocumentItem]:
        calculated_data_document: list[CalculatedDataDocumentItem] = []

        for _, group in group_rows.iterrows():
            aggregation_type = AGGREGATION_LOOKUP[group["Well"]]

            # Samples designated as "Individual" include no calculated data
            if aggregation_type not in CALCULATED_DATA_REFERENCE:
                continue

            group_name = group["Group"].split("(")[0].strip()
            key = str((group_name, group["Target"]))

            ids = group_ids[key]
            calculated_data_ids = {}
            defered_calculated_data_items: list[CalculatedDataItem] = []

            for calculated_data_item in CALCULATED_DATA_REFERENCE[aggregation_type]:
                # TODO: if aggregation type is Replicate(Average), check for required columns
                # Raise if column(s) do not exist

                # Calculated data items that have another calculated data as data source
                # need to be created after the later
                if calculated_data_item.source == CalculatedDataSource.CALCULATED_DATA:
                    defered_calculated_data_items.append(calculated_data_item)
                    continue

                datum_value = float(group[calculated_data_item.column])
                calculated_data_id = random_uuid_str()
                calculated_data_ids[calculated_data_item.name] = calculated_data_id

                data_source_document = [
                    DataSourceDocumentItem(
                        data_source_identifier=identifier,
                        data_source_feature=calculated_data_item.source_feature,
                    )
                    for identifier in ids
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

            # TODO: this should be inproved (repeat less code)
            for calculated_data_item in defered_calculated_data_items:
                datum_value = float(group[calculated_data_item.column])
                calculated_data_id = random_uuid_str()

                data_source_document = [
                    DataSourceDocumentItem(
                        data_source_identifier=calculated_data_ids[source_feature],
                        data_source_feature=source_feature,
                    )
                    for source_feature in calculated_data_item.source_feature.split(",")
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
