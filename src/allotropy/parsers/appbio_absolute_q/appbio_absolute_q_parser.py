from io import IOBase
import uuid

import pandas as pd

from allotropy.allotrope.models.pcr_benchling_2023_09_dpcr import (
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
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueNumber,
    TQuantityValueNumberPerMicroliter,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_reader import AbsoluteQReader
from allotropy.parsers.vendor_parser import VendorParser


class AppbioAbsoluteQParser(VendorParser):
    def _parse(self, raw_contents: IOBase, filename: str) -> Model:
        reader = AbsoluteQReader(raw_contents)
        return self._get_model(reader.wells, filename)

    def _get_model(self, wells: pd.DataFrame, filename: str) -> Model:
        well_groups = wells.groupby(["Well"]).groups.keys()
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
                dPCR_document=[
                    self._get_dpcr_document(wells[wells["Well"] == well])
                    for well in well_groups
                ],
            )
        )

    def _get_dpcr_document(self, well_data: pd.DataFrame) -> DPCRDocumentItem:
        measurement_documents = []
        for _, well_item in well_data.iterrows():
            measurement_documents.append(
                MeasurementDocumentItem(
                    measurement_identifier=str(uuid.uuid4()),
                    measurement_time=self.get_date_time(str(well_item["Date"])),
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
                measurement_document=measurement_documents,
            )
        )
