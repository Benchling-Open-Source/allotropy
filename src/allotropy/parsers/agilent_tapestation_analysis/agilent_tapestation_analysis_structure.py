from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET

from allotropy.parsers.utils.values import (
    get_element_from_xml,
    # get_val_from_xml,
    get_val_from_xml_or_none,
)
from allotropy.types import IOType


@dataclass(frozen=True)
class MetaData:
    analyst: str | None
    analytical_method_identifier: str | None
    data_system_instance_identifier: str | None
    device_identifier: str | None
    equipment_serial_number: str | None
    experimental_data_identifier: str | None
    method_version: str | None
    software_version: str | None

    @staticmethod
    def create(root_element: ET.Element) -> MetaData:
        file_information = get_element_from_xml(root_element, "FileInformation")
        environment = get_element_from_xml(
            root_element, "ScreenTapes/ScreenTape/Environment"
        )

        return MetaData(
            analyst=get_val_from_xml_or_none(environment, "Experimenter"),
            analytical_method_identifier=get_val_from_xml_or_none(
                file_information, "Assay"
            ),
            data_system_instance_identifier=get_val_from_xml_or_none(
                environment, "Computer"
            ),
            device_identifier=get_val_from_xml_or_none(environment, "InstrumentType"),
            equipment_serial_number=get_val_from_xml_or_none(
                environment, "InstrumentSerialNumber"
            ),
            experimental_data_identifier=get_val_from_xml_or_none(
                file_information, "FileName"
            ),
            # If any, only one of those should appear, so we arbitrarily take the first one
            method_version=get_val_from_xml_or_none(file_information, "RINeVersion")
            or get_val_from_xml_or_none(file_information, "DINVersion"),
            software_version=get_val_from_xml_or_none(environment, "AnalysisVersion"),
        )


@dataclass(frozen=True)
class Data:
    root: ET.ElementTree
    metadata: MetaData

    @staticmethod
    def create(contents: IOType) -> Data:
        root = ET.parse(contents)  # noqa: S314
        return Data(root=root, metadata=MetaData.create(root.getroot()))
