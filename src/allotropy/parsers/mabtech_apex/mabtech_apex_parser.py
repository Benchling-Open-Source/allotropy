from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.mabtech_apex.mabtech_apex_contents import MabtechApexContents
from allotropy.parsers.mabtech_apex.mabtech_apex_structure import create_data
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser


class MabtechApexParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Mabtech Apex"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = MabtechApexContents.create(named_file_contents)
        data = create_data(contents, named_file_contents.original_file_name)
        return self._get_mapper(Mapper).map_model(data)
