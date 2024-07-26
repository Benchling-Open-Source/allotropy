from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Model,
)
from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_reader import (
    NanoDropEightReader,
)
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_structure import (
    create_data,
)
from allotropy.parsers.vendor_parser import VendorParser


class NanodropEightParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Thermo Fisher NanoDrop Eight"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        df = NanoDropEightReader.read(named_file_contents)
        data = create_data(df, named_file_contents.original_file_name)
        return self._get_mapper(Mapper).map_model(data)
