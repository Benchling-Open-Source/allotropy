from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET

from allotropy.types import IOType

@dataclass(frozen=True)
class MetaData:
    device_identifier: str
    equipment_serial_number: str
    data_system_instance_identifier: str    # <Computer> (from the first <ScreenTape>/<Enviornment> node)
    software_version: str                   # <AnalysisVersion> (from the first <ScreenTape>/<Enviornment> node)
    analyst: str                            # <Experimenter> (from the first <ScreenTape>/<Enviornment> node)
    analytical_method_identifier: str       # <FileInformation>/<Assay>
    method_version: str                     # <RINeVersion> or <DINVersion>
    experimental_data_identifier: str       # <FileInformation>/<FileName>
    device_identifier: str                  # <InstrumentType>

    @staticmethod
    def create(element_tree: ET.ElementTree):
        pass



@dataclass(frozen=True)
class Data:
    root: ET.ElementTree
    metadata: MetaData

    @staticmethod
    def create(contents: IOType) -> Data:
        root=ET.parse(contents)
        root.find
        return Data(root=root, metadata=MetaData.create(root))
