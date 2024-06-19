# mypy: disallow_any_generics = False

from __future__ import annotations

from allotropy.allotrope.models.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    DataSystemDocument,
    DeviceSystemDocument,
    ElectrophoresisAggregateDocument,
    ElectrophoresisDocumentItem,
    Model,
)
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_structure import (
    Data,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser

SOFTWARE_NAME = "TapeStation Analysis Software"
BRAND_NAME = "TapeStation"
PRODUCT_MANUFACTURER = "Agilent"


class AgilentTapestationAnalysisParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Agilent TapeStation Analysis"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.WORKING_DRAFT

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        data = Data.create(named_file_contents.contents)
        filename = named_file_contents.original_file_name
        return self._get_model(filename, data)

    def _get_model(self, data: Data, filename: str) -> Model:
        _ = data
        return Model(
            electrophoresis_aggregate_document=ElectrophoresisAggregateDocument(
                data_system_document=DataSystemDocument(
                    data_system_instance_identifier="<Computer>",
                    file_name=filename,
                    software_name=SOFTWARE_NAME,
                    software_version="<AnalysisVersion>",
                    ASM_converter_name=f'{ASM_CONVERTER_NAME}_{self.display_name.replace(" ", "_")}'.lower(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                device_system_document=DeviceSystemDocument(
                    brand_name=BRAND_NAME,
                    product_manufacturer=PRODUCT_MANUFACTURER,
                    device_identifier="<InstrumentType>",
                    equipment_serial_number="<InstrumentSerialNumber>",
                ),
                electrophoresis_document=list[ElectrophoresisDocumentItem],
            )
        )
